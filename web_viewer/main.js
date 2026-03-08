/**
 * CarNeRF - 3D Gaussian Splatting 웹 뷰어
 * Three.js 기반 포인트 클라우드 렌더러
 *
 * .ply 파일과 .splat 파일을 로드하여 3D로 렌더링합니다.
 * 마우스/터치로 360도 회전, 줌, 팬이 가능합니다.
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { PLYLoader } from 'three/addons/loaders/PLYLoader.js';

// --- DOM 요소 ---
const canvas = document.getElementById('canvas');
const btnLoad = document.getElementById('btn-load');
const btnReset = document.getElementById('btn-reset');
const fileInput = document.getElementById('file-input');
const infoText = document.getElementById('info-text');
const statsEl = document.getElementById('stats');
const loadingEl = document.getElementById('loading');
const loadingText = document.getElementById('loading-text');
const dropOverlay = document.getElementById('drop-overlay');

// --- Three.js 초기화 ---
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setClearColor(0x1a1a2e);

const scene = new THREE.Scene();

const camera = new THREE.PerspectiveCamera(
    60,
    window.innerWidth / window.innerHeight,
    0.1,
    1000
);
camera.position.set(0, 2, 5);

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.1;
controls.rotateSpeed = 0.8;
controls.zoomSpeed = 1.2;
controls.panSpeed = 0.8;
controls.target.set(0, 0, 0);

// 초기 카메라 상태 저장
const initialCameraPos = camera.position.clone();
const initialTarget = controls.target.clone();

// 기본 조명
const ambientLight = new THREE.AmbientLight(0xffffff, 1.0);
scene.add(ambientLight);

// 그리드 헬퍼 (바닥)
const gridHelper = new THREE.GridHelper(10, 10, 0x444444, 0x333333);
scene.add(gridHelper);

// 현재 로드된 오브젝트
let currentObject = null;

// --- PLY 파일 로드 ---
function loadPLY(buffer, filename) {
    showLoading(`PLY 파일 파싱 중: ${filename}`);

    try {
        const loader = new PLYLoader();
        const geometry = loader.parse(buffer);

        // 기존 오브젝트 제거
        if (currentObject) {
            scene.remove(currentObject);
            currentObject.geometry.dispose();
            currentObject.material.dispose();
        }

        // 색상이 있는지 확인
        const hasColors = geometry.hasAttribute('color');

        // 포인트 크기 결정
        const positions = geometry.getAttribute('position');
        const numPoints = positions.count;

        // 포인트 머티리얼
        const material = new THREE.PointsMaterial({
            size: 0.01,
            sizeAttenuation: true,
            vertexColors: hasColors,
            color: hasColors ? 0xffffff : 0x00aaff,
        });

        const points = new THREE.Points(geometry, material);
        scene.add(points);
        currentObject = points;

        // 모델을 중앙에 배치
        geometry.computeBoundingBox();
        const box = geometry.boundingBox;
        const center = new THREE.Vector3();
        box.getCenter(center);
        points.position.sub(center);

        // 카메라 위치 조정
        const size = new THREE.Vector3();
        box.getSize(size);
        const maxDim = Math.max(size.x, size.y, size.z);
        const distance = maxDim * 2;

        camera.position.set(distance * 0.7, distance * 0.5, distance * 0.7);
        controls.target.set(0, 0, 0);
        controls.update();

        hideLoading();
        infoText.textContent = filename;
        statsEl.textContent = `${numPoints.toLocaleString()}개 포인트 | ${hasColors ? '컬러' : '단색'}`;
    } catch (e) {
        hideLoading();
        infoText.textContent = `오류: ${e.message}`;
        console.error('PLY 로드 실패:', e);
    }
}

// --- SPLAT 파일 로드 ---
function loadSPLAT(buffer, filename) {
    showLoading(`SPLAT 파일 파싱 중: ${filename}`);

    try {
        const data = new DataView(buffer);
        // .splat 포맷: 각 가우시안 32바이트
        // position (3xf32=12) + scale (3xf32=12) + rgba (4xu8=4) + rotation (4xu8=4)
        const numGaussians = Math.floor(buffer.byteLength / 32);

        if (numGaussians === 0) {
            throw new Error('빈 SPLAT 파일입니다.');
        }

        // 기존 오브젝트 제거
        if (currentObject) {
            scene.remove(currentObject);
            currentObject.geometry.dispose();
            currentObject.material.dispose();
        }

        const positions = new Float32Array(numGaussians * 3);
        const colors = new Float32Array(numGaussians * 3);
        const sizes = new Float32Array(numGaussians);

        for (let i = 0; i < numGaussians; i++) {
            const offset = i * 32;

            // Position
            positions[i * 3] = data.getFloat32(offset, true);
            positions[i * 3 + 1] = data.getFloat32(offset + 4, true);
            positions[i * 3 + 2] = data.getFloat32(offset + 8, true);

            // Scale (평균을 크기로 사용)
            const sx = data.getFloat32(offset + 12, true);
            const sy = data.getFloat32(offset + 16, true);
            const sz = data.getFloat32(offset + 20, true);
            sizes[i] = (sx + sy + sz) / 3.0;

            // Color (RGBA)
            colors[i * 3] = data.getUint8(offset + 24) / 255;
            colors[i * 3 + 1] = data.getUint8(offset + 25) / 255;
            colors[i * 3 + 2] = data.getUint8(offset + 26) / 255;
            // opacity = data.getUint8(offset + 27) / 255; // 향후 사용
        }

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        // 포인트 크기: 스케일 중앙값 기반 조정
        const sortedSizes = Array.from(sizes).sort((a, b) => a - b);
        const medianSize = sortedSizes[Math.floor(sortedSizes.length / 2)];
        const pointSize = Math.max(0.002, Math.min(0.05, medianSize * 2));

        const material = new THREE.PointsMaterial({
            size: pointSize,
            sizeAttenuation: true,
            vertexColors: true,
            transparent: true,
            opacity: 0.9,
        });

        const points = new THREE.Points(geometry, material);
        scene.add(points);
        currentObject = points;

        // 중앙 배치
        geometry.computeBoundingBox();
        const box = geometry.boundingBox;
        const center = new THREE.Vector3();
        box.getCenter(center);
        points.position.sub(center);

        // 카메라 조정
        const size = new THREE.Vector3();
        box.getSize(size);
        const maxDim = Math.max(size.x, size.y, size.z);
        const distance = maxDim * 2;

        camera.position.set(distance * 0.7, distance * 0.5, distance * 0.7);
        controls.target.set(0, 0, 0);
        controls.update();

        hideLoading();
        infoText.textContent = filename;
        statsEl.textContent = `${numGaussians.toLocaleString()}개 가우시안 | 포인트 크기: ${pointSize.toFixed(4)}`;
    } catch (e) {
        hideLoading();
        infoText.textContent = `오류: ${e.message}`;
        console.error('SPLAT 로드 실패:', e);
    }
}

// --- 파일 처리 ---
function handleFile(file) {
    const filename = file.name.toLowerCase();
    const reader = new FileReader();

    reader.onload = (e) => {
        const buffer = e.target.result;
        if (filename.endsWith('.ply')) {
            loadPLY(buffer, file.name);
        } else if (filename.endsWith('.splat')) {
            loadSPLAT(buffer, file.name);
        } else {
            infoText.textContent = '지원하지 않는 형식입니다. (.ply 또는 .splat)';
        }
    };

    reader.onerror = () => {
        infoText.textContent = '파일 읽기 실패';
    };

    reader.readAsArrayBuffer(file);
}

// --- UI 유틸 ---
function showLoading(text) {
    loadingText.textContent = text || '로딩 중...';
    loadingEl.style.display = 'flex';
}

function hideLoading() {
    loadingEl.style.display = 'none';
}

// --- 이벤트 핸들러 ---

// 파일 로드 버튼
btnLoad.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
        e.target.value = ''; // 같은 파일 다시 로드 가능하게
    }
});

// 카메라 리셋
btnReset.addEventListener('click', () => {
    if (currentObject) {
        const geometry = currentObject.geometry;
        geometry.computeBoundingBox();
        const box = geometry.boundingBox;
        const size = new THREE.Vector3();
        box.getSize(size);
        const maxDim = Math.max(size.x, size.y, size.z);
        const distance = maxDim * 2;

        camera.position.set(distance * 0.7, distance * 0.5, distance * 0.7);
    } else {
        camera.position.copy(initialCameraPos);
    }
    controls.target.set(0, 0, 0);
    controls.update();
});

// 드래그 앤 드롭
document.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropOverlay.style.display = 'flex';
});

document.addEventListener('dragleave', (e) => {
    if (e.target === dropOverlay || e.target === document.documentElement) {
        dropOverlay.style.display = 'none';
    }
});

document.addEventListener('drop', (e) => {
    e.preventDefault();
    dropOverlay.style.display = 'none';
    if (e.dataTransfer.files.length > 0) {
        handleFile(e.dataTransfer.files[0]);
    }
});

// 윈도우 리사이즈
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

// --- 렌더 루프 ---
function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}

animate();