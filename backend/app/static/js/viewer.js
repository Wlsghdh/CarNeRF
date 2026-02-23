/**
 * CarNeRF Embeddable 3D Viewer
 * Gaussian Splatting renderer using @mkkellogg/gaussian-splats-3d
 */

import * as GaussianSplats3D from '@mkkellogg/gaussian-splats-3d';

export function initViewer(containerId, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;

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

    // Set background color
    try { viewer.renderer.setClearColor(backgroundColor); } catch (_) {}

    async function loadModelFromURL(url) {
        try {
            await viewer.addSplatScene(url, {
                progressiveLoad: true,
            });
            viewer.start();

            // Apply settings after viewer is started
            try { viewer.renderer.setClearColor(backgroundColor); } catch (_) {}

            if (autoRotate) {
                if (viewer.controls && 'autoRotate' in viewer.controls) {
                    viewer.controls.autoRotate = true;
                    viewer.controls.autoRotateSpeed = 1.5;
                } else {
                    // Fallback: manual Y-axis orbit
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

    // Auto-load if URL provided
    if (modelUrl) {
        loadModelFromURL(modelUrl);
    }

    return { loadModelFromURL };
}
