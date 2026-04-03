document.addEventListener('DOMContentLoaded', () => {
    // Image preview
    const imageInput = document.getElementById('image-input');
    const imagePreview = document.getElementById('image-preview');

    if (imageInput) {
        imageInput.addEventListener('change', async () => {
            imagePreview.innerHTML = '';
            const files = Array.from(imageInput.files).slice(0, 10);

            // Show previews immediately
            files.forEach((file) => {
                const reader = new FileReader();
                reader.onload = (e) => {
                    const div = document.createElement('div');
                    div.className = 'img-thumb';
                    div.innerHTML = `<img src="${e.target.result}" alt="preview">`;
                    imagePreview.appendChild(div);
                };
                reader.readAsDataURL(file);
            });

            // Upload to server
            if (files.length > 0) {
                const formData = new FormData();
                files.forEach(f => formData.append('files', f));
                try {
                    const res = await fetch('/api/upload/images', {
                        method: 'POST',
                        body: formData,
                    });
                    if (res.ok) {
                        const data = await res.json();
                        uploadedImageUrls = data.files.map(f => f.url);
                    }
                } catch (e) {
                    console.warn('Image upload failed:', e);
                }
            }
        });
    }

    // --- 3D Scan: Quality selection + Video upload + pipeline polling ---
    const videoInput = document.getElementById('video-input');
    const videoFilename = document.getElementById('video-filename');
    const scanUploadArea = document.getElementById('scan-upload-area');
    const scanProgress = document.getElementById('scan-progress');
    const scanProgressBar = document.getElementById('scan-progress-bar');
    const scanStatusText = document.getElementById('scan-status-text');
    const scanMessage = document.getElementById('scan-message');
    const scanDone = document.getElementById('scan-done');
    const scanViewLink = document.getElementById('scan-view-link');
    const scanProgressPct = document.getElementById('scan-progress-pct');
    const scanElapsed = document.getElementById('scan-elapsed');
    const scanEstTime = document.getElementById('scan-est-time');
    const qualitySelector = document.getElementById('quality-selector');

    // Track pipeline result for form submission
    let pipelineVehicleId = null;
    let pipelineModelUrl = null;
    let selectedQuality = 'hq';
    let pipelineStartTime = null;
    let elapsedTimer = null;
    let uploadedImageUrls = [];

    // Quality selection
    window.selectQuality = function(quality) {
        selectedQuality = quality;
        document.querySelectorAll('.quality-opt').forEach(el => {
            el.classList.toggle('selected', el.dataset.quality === quality);
        });
    };

    // Step indicator labels
    const STEP_LABELS = {
        1: '프레임 추출',
        2: 'COLMAP',
        3: '배경 제거',
        4: 'Depth Map',
        5: '학습',
        6: '변환',
        7: '완료',
    };

    function updateStepIndicator(currentStep, failed = false) {
        document.querySelectorAll('.step-dot').forEach(dot => {
            const step = parseInt(dot.dataset.step);
            dot.classList.remove('active', 'done', 'failed');
            if (failed && step === currentStep) {
                dot.classList.add('failed');
            } else if (step < currentStep) {
                dot.classList.add('done');
            } else if (step === currentStep) {
                dot.classList.add('active');
            }
        });
        document.querySelectorAll('.step-line').forEach(line => {
            const afterStep = parseInt(line.dataset.after);
            line.classList.remove('done', 'active');
            if (afterStep < currentStep) {
                line.classList.add('done');
            } else if (afterStep === currentStep) {
                line.classList.add('active');
            }
        });
    }

    function updateElapsedTime() {
        if (!pipelineStartTime) return;
        const elapsed = Math.floor((Date.now() - pipelineStartTime) / 1000);
        const min = Math.floor(elapsed / 60);
        const sec = elapsed % 60;
        if (scanElapsed) {
            scanElapsed.textContent = `경과: ${min}분 ${sec < 10 ? '0' : ''}${sec}초`;
        }
    }

    if (videoInput) {
        videoInput.addEventListener('change', async () => {
            const file = videoInput.files[0];
            if (!file) return;

            // Show filename
            if (videoFilename) {
                videoFilename.textContent = file.name;
                videoFilename.style.display = 'block';
            }

            // Upload video
            scanUploadArea.style.opacity = '0.5';
            scanUploadArea.style.pointerEvents = 'none';
            if (qualitySelector) qualitySelector.style.display = 'none';
            scanProgress.style.display = 'block';
            scanStatusText.textContent = '영상을 업로드하고 있습니다...';
            scanProgressBar.style.width = '2%';
            scanMessage.textContent = '';
            updateStepIndicator(0);

            const formData = new FormData();
            formData.append('video', file);
            formData.append('quality', selectedQuality);

            // Detail box
            const detailQuality = document.getElementById('detail-quality');
            if (detailQuality) {
                const qNames = { standard: 'Standard (30K)', hq: 'HQ (60K)', ultra: 'Ultra (80K)' };
                detailQuality.textContent = qNames[selectedQuality] || selectedQuality;
            }

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
                pipelineStartTime = Date.now();
                scanProgressBar.style.width = '3%';
                scanStatusText.textContent = '파이프라인 시작됨';

                // Start elapsed timer
                elapsedTimer = setInterval(updateElapsedTime, 1000);

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

                // Update step indicator
                const step = job.step || 0;
                updateStepIndicator(step, job.status === 'failed');

                // Update progress bar
                const progress = job.progress || 0;
                scanProgressBar.style.width = progress + '%';
                if (scanProgressPct) scanProgressPct.textContent = progress + '%';

                // Update status text
                scanStatusText.textContent = job.label || job.status;
                if (job.message) scanMessage.textContent = job.message;

                // Update est time
                if (scanEstTime && job.est_time) {
                    scanEstTime.textContent = '예상: ' + job.est_time;
                }

                // Update detail box
                if (job.frame_count) {
                    const el = document.getElementById('detail-frames');
                    if (el) el.textContent = job.frame_count + '장';
                }
                if (job.bg_removed !== undefined) {
                    const el = document.getElementById('detail-bg');
                    if (el) el.textContent = job.bg_removed ? '완료' : '스킵';
                    if (el && job.bg_removed) el.style.color = '#10B981';
                }
                if (job.depth_generated !== undefined) {
                    const el = document.getElementById('detail-depth');
                    if (el) el.textContent = job.depth_generated ? '완료' : '스킵';
                    if (el && job.depth_generated) el.style.color = '#10B981';
                }
                if (job.iterations) {
                    const el = document.getElementById('detail-iter');
                    if (el) el.textContent = job.iterations.toLocaleString() + ' iter';
                }

                if (job.status === 'completed') {
                    clearInterval(interval);
                    if (elapsedTimer) clearInterval(elapsedTimer);
                    pipelineModelUrl = job.model_url;
                    scanProgress.style.display = 'none';
                    scanDone.style.display = 'block';

                    const doneInfo = document.getElementById('scan-done-info');
                    if (doneInfo && job.elapsed_seconds) {
                        const min = Math.floor(job.elapsed_seconds / 60);
                        doneInfo.textContent = `${min}분 만에 고품질 3D 모델이 생성되었습니다.`;
                    }

                    if (pipelineVehicleId) {
                        scanViewLink.href = `/viewer/${pipelineVehicleId}`;
                    }
                } else if (job.status === 'failed') {
                    clearInterval(interval);
                    if (elapsedTimer) clearInterval(elapsedTimer);
                    scanProgressBar.style.background = 'linear-gradient(90deg, #EF4444, #DC2626)';
                    scanStatusText.style.color = '#EF4444';
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
            formMessage.style.display = 'none';

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

            // 업로드된 이미지 URL 첨부
            if (uploadedImageUrls.length > 0) {
                data.image_urls = uploadedImageUrls;
            }

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
                    formMessage.className = 'form-msg error';
                    formMessage.style.display = 'block';
                    setTimeout(() => { window.location.href = '/login'; }, 1500);
                    return;
                }

                const result = await res.json();
                if (!res.ok) {
                    formMessage.textContent = result.detail || '등록에 실패했습니다.';
                    formMessage.className = 'form-msg error';
                    formMessage.style.display = 'block';
                    return;
                }

                formMessage.textContent = '매물이 등록되었습니다! 상세 페이지로 이동합니다.';
                formMessage.className = 'form-msg success';
                formMessage.style.display = 'block';
                setTimeout(() => {
                    window.location.href = `/vehicles/${result.vehicle.id}`;
                }, 1500);
            } catch {
                formMessage.textContent = '서버 오류가 발생했습니다.';
                formMessage.className = 'form-msg error';
                formMessage.style.display = 'block';
            }
        });
    }
});
