document.addEventListener('DOMContentLoaded', () => {
    // Image preview
    const imageInput = document.getElementById('image-input');
    const imagePreview = document.getElementById('image-preview');

    if (imageInput) {
        imageInput.addEventListener('change', () => {
            imagePreview.innerHTML = '';
            const files = Array.from(imageInput.files).slice(0, 10);
            files.forEach((file) => {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const div = document.createElement('div');
                    div.className = 'aspect-square rounded-lg overflow-hidden bg-gray-100';
                    div.innerHTML = `<img src="${e.target.result}" class="w-full h-full object-cover" alt="preview">`;
                    imagePreview.appendChild(div);
                };
                reader.readAsDataURL(file);
            });
        });
    }

    // --- 3D Scan: Video upload + pipeline polling ---
    const videoInput = document.getElementById('video-input');
    const videoFilename = document.getElementById('video-filename');
    const scanUploadArea = document.getElementById('scan-upload-area');
    const scanProgress = document.getElementById('scan-progress');
    const scanProgressBar = document.getElementById('scan-progress-bar');
    const scanStatusText = document.getElementById('scan-status-text');
    const scanMessage = document.getElementById('scan-message');
    const scanDone = document.getElementById('scan-done');
    const scanViewLink = document.getElementById('scan-view-link');

    // Track pipeline result for form submission
    let pipelineVehicleId = null;
    let pipelineModelUrl = null;

    const STATUS_MAP = {
        queued:            { text: '대기 중...', pct: 5 },
        extracting_frames: { text: '프레임 추출 중...', pct: 15 },
        colmap:            { text: '카메라 위치 추정 중 (COLMAP)...', pct: 35 },
        training:          { text: '3D Gaussian Splatting 학습 중...', pct: 65 },
        exporting:         { text: '웹 뷰어용 모델 변환 중...', pct: 85 },
        completed:         { text: '완료!', pct: 100 },
        failed:            { text: '실패', pct: 0 },
    };

    if (videoInput) {
        videoInput.addEventListener('change', async () => {
            const file = videoInput.files[0];
            if (!file) return;

            // Show filename
            videoFilename.textContent = file.name;
            videoFilename.classList.remove('hidden');

            // Upload video
            scanUploadArea.classList.add('opacity-50', 'pointer-events-none');
            scanProgress.classList.remove('hidden');
            scanStatusText.textContent = '영상을 업로드하고 있습니다...';
            scanProgressBar.style.width = '2%';
            scanMessage.textContent = '';

            const formData = new FormData();
            formData.append('video', file);

            try {
                const res = await fetch('/api/pipeline/start', {
                    method: 'POST',
                    body: formData,
                });

                if (res.status === 401) {
                    scanStatusText.textContent = '로그인이 필요합니다.';
                    scanMessage.textContent = '로그인 후 다시 시도해 주세요.';
                    scanProgressBar.style.width = '0%';
                    setTimeout(() => { window.location.href = '/login'; }, 2000);
                    return;
                }

                const result = await res.json();
                if (!res.ok) {
                    scanStatusText.textContent = '업로드 실패';
                    scanMessage.textContent = result.detail || '오류가 발생했습니다.';
                    scanProgressBar.style.width = '0%';
                    return;
                }

                pipelineVehicleId = result.vehicle_id;
                scanProgressBar.style.width = '5%';
                scanStatusText.textContent = '파이프라인 시작됨';

                // Start polling
                pollPipelineStatus(result.job_id);
            } catch (err) {
                scanStatusText.textContent = '업로드 실패';
                scanMessage.textContent = '서버에 연결할 수 없습니다.';
                scanProgressBar.style.width = '0%';
            }
        });
    }

    function pollPipelineStatus(jobId) {
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/pipeline/status/${jobId}`);
                if (!res.ok) {
                    clearInterval(interval);
                    scanStatusText.textContent = '상태 조회 실패';
                    return;
                }

                const job = await res.json();
                const info = STATUS_MAP[job.status] || { text: job.status, pct: 50 };

                scanStatusText.textContent = info.text;
                scanProgressBar.style.width = info.pct + '%';
                if (job.message) {
                    scanMessage.textContent = job.message;
                }

                if (job.status === 'completed') {
                    clearInterval(interval);
                    pipelineModelUrl = job.model_url;
                    scanProgress.classList.add('hidden');
                    scanDone.classList.remove('hidden');
                    if (pipelineVehicleId) {
                        scanViewLink.href = `/viewer/${pipelineVehicleId}`;
                    }
                } else if (job.status === 'failed') {
                    clearInterval(interval);
                    scanProgressBar.classList.remove('bg-primary-600');
                    scanProgressBar.classList.add('bg-red-500');
                }
            } catch {
                // Network error, keep polling
            }
        }, 3000);
    }

    // Form submission
    const sellForm = document.getElementById('sell-form');
    const formMessage = document.getElementById('form-message');

    if (sellForm) {
        sellForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            formMessage.classList.add('hidden');

            const form = e.target;
            const data = {
                title: form.title.value,
                description: form.description.value || null,
                price: parseInt(form.price.value),
                is_negotiable: form.is_negotiable.checked,
                brand: form.brand.value,
                model: form.model.value,
                year: parseInt(form.year.value),
                trim: form.trim.value || null,
                fuel_type: form.fuel_type.value,
                transmission: form.transmission.value,
                mileage: parseInt(form.mileage.value),
                color: form.color.value || null,
                engine_cc: form.engine_cc.value ? parseInt(form.engine_cc.value) : null,
                region: form.region.value || null,
            };

            // If pipeline created a vehicle, attach its ID
            if (pipelineVehicleId) {
                data.vehicle_id = pipelineVehicleId;
            }

            try {
                const res = await fetch('/api/listings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data),
                });

                if (res.status === 401) {
                    formMessage.textContent = '로그인이 필요합니다.';
                    formMessage.className = 'text-center p-4 rounded-xl bg-red-50 text-red-600';
                    formMessage.classList.remove('hidden');
                    setTimeout(() => { window.location.href = '/login'; }, 1500);
                    return;
                }

                const result = await res.json();
                if (!res.ok) {
                    formMessage.textContent = result.detail || '등록에 실패했습니다.';
                    formMessage.className = 'text-center p-4 rounded-xl bg-red-50 text-red-600';
                    formMessage.classList.remove('hidden');
                    return;
                }

                formMessage.textContent = '매물이 등록되었습니다! 상세 페이지로 이동합니다.';
                formMessage.className = 'text-center p-4 rounded-xl bg-green-50 text-green-600';
                formMessage.classList.remove('hidden');
                setTimeout(() => {
                    window.location.href = `/vehicles/${result.vehicle.id}`;
                }, 1500);
            } catch {
                formMessage.textContent = '서버 오류가 발생했습니다.';
                formMessage.className = 'text-center p-4 rounded-xl bg-red-50 text-red-600';
                formMessage.classList.remove('hidden');
            }
        });
    }
});
