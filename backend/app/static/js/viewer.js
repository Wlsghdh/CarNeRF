/**
 * CarNeRF Embeddable 3D Viewer
 * Gaussian Splatting renderer + AI 결함 마커 시스템
 */

import * as GaussianSplats3D from '@mkkellogg/gaussian-splats-3d';
import * as THREE from 'three';

let _viewer = null;
let _container = null;
let _defectMarkers = [];
let _defectData = null;
let _markersVisible = false;
let _animationId = null;
let _raycaster = new THREE.Raycaster();
let _mouse = new THREE.Vector2();

export function initViewer(containerId, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;
    _container = container;

    const {
        modelUrl = null,
        autoRotate = false,
        backgroundColor = 0x1a1a2e,
    } = options;

    const viewer = new GaussianSplats3D.Viewer({
        rootElement: container,
        cameraUp: [0, -1, 0],
        initialCameraPosition: [5, -3, 8],
        initialCameraLookAt: [0, 0, 0],
        sharedMemoryForWorkers: false,
    });
    _viewer = viewer;

    try { viewer.renderer.setClearColor(backgroundColor); } catch (_) {}

    async function loadModelFromURL(url) {
        try {
            await viewer.addSplatScene(url, {
                progressiveLoad: true,
            });
            viewer.start();
            try { viewer.renderer.setClearColor(backgroundColor); } catch (_) {}

            if (autoRotate) {
                if (viewer.controls && 'autoRotate' in viewer.controls) {
                    viewer.controls.autoRotate = true;
                    viewer.controls.autoRotateSpeed = 1.5;
                } else {
                    const speed = 0.003;
                    (function rotateLoop() {
                        requestAnimationFrame(rotateLoop);
                        try {
                            const cam = viewer.camera;
                            if (!cam) return;
                            const x = cam.position.x;
                            const z = cam.position.z;
                            const cos = Math.cos(speed);
                            const sin = Math.sin(speed);
                            cam.position.x = x * cos - z * sin;
                            cam.position.z = x * sin + z * cos;
                            cam.lookAt(0, 0, 0);
                        } catch (_) {}
                    })();
                }
            }
        } catch (e) {
            console.error('Model load failed:', e);
        }
    }

    if (modelUrl) {
        loadModelFromURL(modelUrl);
    }

    return { loadModelFromURL, getViewer: () => viewer };
}


/**
 * 결함 마커 시스템
 * - 3D 위치에 펄스 애니메이션 마커 표시
 * - 마우스 hover → 썸네일
 * - 클릭 → 2D 사진 모달
 */
export function initDefectMarkers(vehicleId) {
    fetch(`/api/defect/vehicles/${vehicleId}`)
        .then(r => r.json())
        .then(data => {
            _defectData = data;
            if (data.defects && data.defects.length > 0) {
                // 결함 개수 뱃지 업데이트
                const badge = document.getElementById('defect-count-badge');
                if (badge) {
                    badge.textContent = data.defects.length;
                    badge.style.display = 'inline-flex';
                }
                const scoreEl = document.getElementById('defect-score-value');
                if (scoreEl) scoreEl.textContent = data.total_defect_score;
                const levelEl = document.getElementById('defect-severity-level');
                if (levelEl) {
                    levelEl.textContent = data.severity_level;
                    const colors = { '양호': '#10B981', '경미': '#10B981', '중간': '#F59E0B', '심각': '#EF4444' };
                    levelEl.style.color = colors[data.severity_level] || '#F59E0B';
                }
            }
        })
        .catch(e => console.error('Defect data load failed:', e));
}


export function toggleDefectMarkers() {
    _markersVisible = !_markersVisible;

    const btn = document.getElementById('toggle-defects-btn');
    if (btn) {
        btn.classList.toggle('active', _markersVisible);
    }

    if (_markersVisible) {
        createMarkerOverlay();
        startMarkerAnimation();
    } else {
        removeMarkerOverlay();
        if (_animationId) {
            cancelAnimationFrame(_animationId);
            _animationId = null;
        }
    }
    return _markersVisible;
}


function createMarkerOverlay() {
    if (!_defectData || !_defectData.defects) return;
    removeMarkerOverlay();

    // 마커 오버레이 컨테이너
    let overlay = document.getElementById('defect-overlay');
    if (!overlay) {
        overlay = document.createElement('div');
        overlay.id = 'defect-overlay';
        overlay.style.cssText = 'position:absolute;inset:0;pointer-events:none;z-index:10;overflow:hidden;';
        _container.style.position = 'relative';
        _container.appendChild(overlay);
    }

    // 툴팁
    let tooltip = document.getElementById('defect-tooltip');
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.id = 'defect-tooltip';
        tooltip.style.cssText = `
            position:absolute; display:none; z-index:20;
            background:rgba(14,17,23,0.95); border:1px solid rgba(255,255,255,0.15);
            border-radius:12px; padding:12px; min-width:200px;
            pointer-events:none; backdrop-filter:blur(12px);
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        `;
        overlay.appendChild(tooltip);
    }

    _defectMarkers = [];
    _defectData.defects.forEach((defect, i) => {
        const marker = document.createElement('div');
        marker.className = 'defect-marker';
        marker.dataset.index = i;
        marker.style.cssText = `
            position:absolute; width:24px; height:24px;
            pointer-events:auto; cursor:pointer;
            transform:translate(-50%,-50%);
        `;

        // 내부 펄스 원
        const inner = document.createElement('div');
        inner.style.cssText = `
            width:12px; height:12px;
            background:${defect.marker_color};
            border-radius:50%;
            position:absolute; top:50%; left:50%;
            transform:translate(-50%,-50%);
            box-shadow: 0 0 8px ${defect.marker_color}, 0 0 16px ${defect.marker_color}80;
            z-index:2;
        `;
        marker.appendChild(inner);

        // 펄스 링
        const pulse = document.createElement('div');
        pulse.style.cssText = `
            width:24px; height:24px;
            border:2px solid ${defect.marker_color};
            border-radius:50%;
            position:absolute; top:50%; left:50%;
            transform:translate(-50%,-50%);
            animation: defectPulse 1.5s ease-out infinite;
            opacity:0.7;
        `;
        marker.appendChild(pulse);

        // 두 번째 펄스 (지연)
        const pulse2 = document.createElement('div');
        pulse2.style.cssText = pulse.style.cssText + 'animation-delay:0.75s;';
        marker.appendChild(pulse2);

        // hover 이벤트
        marker.addEventListener('mouseenter', (e) => {
            showTooltip(defect, e);
        });
        marker.addEventListener('mouseleave', () => {
            tooltip.style.display = 'none';
        });
        // 클릭 → 모달
        marker.addEventListener('click', () => {
            showDefectModal(defect);
        });

        overlay.appendChild(marker);
        _defectMarkers.push({ el: marker, defect });
    });

    // CSS 애니메이션 추가
    if (!document.getElementById('defect-pulse-style')) {
        const style = document.createElement('style');
        style.id = 'defect-pulse-style';
        style.textContent = `
            @keyframes defectPulse {
                0%   { transform:translate(-50%,-50%) scale(1); opacity:0.7; }
                100% { transform:translate(-50%,-50%) scale(2.5); opacity:0; }
            }
        `;
        document.head.appendChild(style);
    }
}


function showTooltip(defect, event) {
    const tooltip = document.getElementById('defect-tooltip');
    if (!tooltip) return;

    const severityColors = {
        '경미': '#10B981', '중간': '#F59E0B', '심각': '#EF4444'
    };
    const sevColor = severityColors[defect.severity] || '#F59E0B';

    tooltip.innerHTML = `
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            <div style="width:8px;height:8px;background:${defect.marker_color};border-radius:50%;"></div>
            <span style="font-size:13px;font-weight:700;color:#E2E8F0;">${defect.type_kr}</span>
            <span style="font-size:11px;padding:2px 8px;border-radius:10px;background:${sevColor}20;color:${sevColor};border:1px solid ${sevColor}40;font-weight:600;">${defect.severity}</span>
        </div>
        <p style="font-size:12px;color:#94A3B8;line-height:1.5;margin:0 0 6px 0;">${defect.description}</p>
        <div style="font-size:11px;color:#64748B;">
            신뢰도: ${Math.round(defect.confidence * 100)}%
            <span style="margin-left:8px;color:#0EA5E9;cursor:pointer;">클릭하여 상세보기</span>
        </div>
    `;

    // 위치 계산
    const rect = _container.getBoundingClientRect();
    const markerRect = event.target.closest('.defect-marker').getBoundingClientRect();
    let x = markerRect.left - rect.left + 20;
    let y = markerRect.top - rect.top - 10;

    // 오른쪽 넘침 방지
    if (x + 220 > rect.width) x = markerRect.left - rect.left - 220;
    // 위쪽 넘침 방지
    if (y < 0) y = markerRect.top - rect.top + 30;

    tooltip.style.left = x + 'px';
    tooltip.style.top = y + 'px';
    tooltip.style.display = 'block';
}


function startMarkerAnimation() {
    function updatePositions() {
        if (!_markersVisible || !_viewer) return;

        const camera = _viewer.camera;
        if (!camera) {
            _animationId = requestAnimationFrame(updatePositions);
            return;
        }

        const width = _container.clientWidth;
        const height = _container.clientHeight;

        _defectMarkers.forEach(({ el, defect }) => {
            const pos = defect.position_3d;
            const vec = new THREE.Vector3(pos[0], pos[1], pos[2]);
            vec.project(camera);

            const x = (vec.x * 0.5 + 0.5) * width;
            const y = (-vec.y * 0.5 + 0.5) * height;
            const behind = vec.z > 1;

            if (behind || x < -20 || x > width + 20 || y < -20 || y > height + 20) {
                el.style.display = 'none';
            } else {
                el.style.display = 'block';
                el.style.left = x + 'px';
                el.style.top = y + 'px';
            }
        });

        _animationId = requestAnimationFrame(updatePositions);
    }
    _animationId = requestAnimationFrame(updatePositions);
}


function removeMarkerOverlay() {
    const overlay = document.getElementById('defect-overlay');
    if (overlay) overlay.innerHTML = '';
    _defectMarkers = [];
}


function showDefectModal(defect) {
    // 기존 모달 제거
    let modal = document.getElementById('defect-modal');
    if (modal) modal.remove();

    const severityColors = {
        '경미': '#10B981', '중간': '#F59E0B', '심각': '#EF4444'
    };
    const sevColor = severityColors[defect.severity] || '#F59E0B';

    modal = document.createElement('div');
    modal.id = 'defect-modal';
    modal.style.cssText = `
        position:fixed; inset:0; z-index:9999;
        display:flex; align-items:center; justify-content:center;
        background:rgba(0,0,0,0.75); backdrop-filter:blur(8px);
    `;

    modal.innerHTML = `
        <div style="
            background:#0E1117; border:1px solid rgba(255,255,255,0.1);
            border-radius:20px; max-width:600px; width:90%; max-height:85vh;
            overflow-y:auto; box-shadow:0 24px 64px rgba(0,0,0,0.5);
        ">
            <!-- 헤더 -->
            <div style="padding:24px 24px 0; display:flex; justify-content:space-between; align-items:center;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <div style="width:10px;height:10px;background:${defect.marker_color};border-radius:50%;box-shadow:0 0 8px ${defect.marker_color};"></div>
                    <h3 style="font-size:18px;font-weight:800;color:#E2E8F0;margin:0;">
                        결함 발견: ${defect.type_kr}
                    </h3>
                    <span style="font-size:12px;padding:3px 10px;border-radius:12px;background:${sevColor}15;color:${sevColor};border:1px solid ${sevColor}30;font-weight:600;">
                        ${defect.severity}
                    </span>
                </div>
                <button onclick="document.getElementById('defect-modal').remove()"
                    style="width:32px;height:32px;background:rgba(255,255,255,0.08);border:none;border-radius:8px;color:#94A3B8;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;"
                    onmouseover="this.style.background='rgba(255,255,255,0.15)'"
                    onmouseout="this.style.background='rgba(255,255,255,0.08)'"
                >&times;</button>
            </div>

            <!-- 이미지 -->
            <div style="padding:16px 24px;">
                <div style="
                    background:#161B24; border:1px solid rgba(255,255,255,0.08);
                    border-radius:12px; overflow:hidden; aspect-ratio:16/10;
                    display:flex; align-items:center; justify-content:center;
                    position:relative;
                ">
                    <img src="${defect.annotated_image_url}"
                         style="width:100%;height:100%;object-fit:cover;"
                         onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
                    <div style="display:none;flex-direction:column;align-items:center;gap:8px;color:#64748B;">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z"/>
                        </svg>
                        <span style="font-size:13px;">결함 부위 이미지</span>
                    </div>
                </div>
            </div>

            <!-- 상세 정보 -->
            <div style="padding:0 24px 24px;">
                <div style="
                    background:#161B24; border:1px solid rgba(255,255,255,0.08);
                    border-radius:12px; padding:16px;
                ">
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
                        <div>
                            <div style="font-size:11px;color:#64748B;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.5px;">결함 유형</div>
                            <div style="font-size:14px;font-weight:600;color:#E2E8F0;">${defect.type_kr} (${defect.type})</div>
                        </div>
                        <div>
                            <div style="font-size:11px;color:#64748B;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.5px;">심각도</div>
                            <div style="font-size:14px;font-weight:600;color:${sevColor};">${defect.severity}</div>
                        </div>
                        <div>
                            <div style="font-size:11px;color:#64748B;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.5px;">AI 신뢰도</div>
                            <div style="font-size:14px;font-weight:600;color:#E2E8F0;">${Math.round(defect.confidence * 100)}%</div>
                        </div>
                        <div>
                            <div style="font-size:11px;color:#64748B;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.5px;">소스 프레임</div>
                            <div style="font-size:14px;font-weight:600;color:#E2E8F0;">${defect.source_frame}</div>
                        </div>
                    </div>
                    <div style="border-top:1px solid rgba(255,255,255,0.08);padding-top:12px;">
                        <div style="font-size:11px;color:#64748B;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.5px;">AI 분석 소견</div>
                        <div style="font-size:13px;color:#94A3B8;line-height:1.7;">${defect.description}</div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // 배경 클릭으로 닫기
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
    // ESC로 닫기
    const escHandler = (e) => {
        if (e.key === 'Escape') { modal.remove(); document.removeEventListener('keydown', escHandler); }
    };
    document.addEventListener('keydown', escHandler);

    document.body.appendChild(modal);
}
