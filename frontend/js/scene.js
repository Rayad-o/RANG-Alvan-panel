// صحنه‌های سه‌بعدی (Three.js). اگر Three.js یا WebGL در دسترس نباشد، همه‌چیز بی‌صدا غیرفعال می‌شود
// و صفحه با نسخهٔ دوبعدی کار می‌کند.
(function () {
    const REDUCED = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function makeRenderer(canvas) {
        if (!window.THREE) return null;
        try {
            const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
            renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
            return renderer;
        } catch (e) {
            return null;
        }
    }

    // حلقهٔ رندر مشترک: وقتی تب پنهان یا عنصر خارج از دید است، رندر متوقف می‌شود
    function loop(canvas, draw) {
        let running = true;
        let visible = true;
        let raf = 0;
        const start = performance.now();

        function frame(now) {
            raf = 0;
            if (!running) return;
            if (visible && !document.hidden) draw((now - start) / 1000);
            if (!REDUCED) raf = requestAnimationFrame(frame);
        }
        const kick = () => { if (!raf && running) raf = requestAnimationFrame(frame); };

        if ("IntersectionObserver" in window) {
            new IntersectionObserver(entries => {
                visible = entries[0].isIntersecting;
                if (visible) kick();
            }).observe(canvas);
        }
        document.addEventListener("visibilitychange", kick);
        kick();
        return () => { running = false; cancelAnimationFrame(raf); };
    }

    function fit(renderer, camera, host) {
        const w = host.clientWidth || 1;
        const h = host.clientHeight || 1;
        renderer.setSize(w, h, false);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
    }

    // ------------------------------------------------------------------
    // پس‌زمینهٔ صفحهٔ ورود: چند شکل شیشه‌ای که آرام شناورند
    // ------------------------------------------------------------------
    function background(canvas) {
        const renderer = makeRenderer(canvas);
        if (!renderer) return;

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
        camera.position.z = 10;

        scene.add(new THREE.AmbientLight(0xffffff, 0.55));
        const key = new THREE.PointLight(0x9aa5ff, 1.4, 60);
        key.position.set(5, 6, 8);
        scene.add(key);
        const rim = new THREE.PointLight(0x22d3ee, 1.1, 60);
        rim.position.set(-6, -4, 5);
        scene.add(rim);

        const group = new THREE.Group();
        scene.add(group);

        const shapes = [
            { geo: new THREE.IcosahedronGeometry(1.5, 0), color: 0x6366f1, pos: [3.6, 1.2, -1], spin: [0.12, 0.18] },
            { geo: new THREE.TorusGeometry(1.05, 0.34, 24, 72), color: 0x22d3ee, pos: [-4.2, -1.6, -2], spin: [0.2, 0.1] },
            { geo: new THREE.OctahedronGeometry(0.9, 0), color: 0xa78bfa, pos: [-2.6, 2.8, -3], spin: [0.15, 0.22], wire: true },
        ].map(s => {
            const material = s.wire
                ? new THREE.MeshBasicMaterial({ color: s.color, wireframe: true, transparent: true, opacity: 0.55 })
                : new THREE.MeshStandardMaterial({ color: s.color, metalness: 0.35, roughness: 0.3, flatShading: true, transparent: true, opacity: 0.88 });
            const mesh = new THREE.Mesh(s.geo, material);
            mesh.position.set(...s.pos);
            group.add(mesh);
            return { mesh, base: s.pos, spin: s.spin };
        });

        const pointer = { x: 0, y: 0 };
        window.addEventListener("pointermove", e => {
            pointer.x = (e.clientX / window.innerWidth - 0.5) * 2;
            pointer.y = (e.clientY / window.innerHeight - 0.5) * 2;
        });

        function resize() {
            renderer.setSize(window.innerWidth, window.innerHeight, false);
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            group.scale.setScalar(camera.aspect < 0.9 ? 0.62 : 1);
        }
        resize();
        window.addEventListener("resize", resize);

        loop(canvas, t => {
            shapes.forEach((s, i) => {
                s.mesh.rotation.x = t * s.spin[0];
                s.mesh.rotation.y = t * s.spin[1];
                s.mesh.position.y = s.base[1] + Math.sin(t * 0.6 + i * 2) * 0.25;
            });
            group.rotation.y += (pointer.x * 0.18 - group.rotation.y) * 0.04;
            group.rotation.x += (pointer.y * 0.1 - group.rotation.x) * 0.04;
            renderer.render(scene, camera);
        });
    }

    // ------------------------------------------------------------------
    // نمودار میله‌ای سه‌بعدی
    // data: [{ label, value, tip }]، format: عدد → متن کوتاه
    // ------------------------------------------------------------------
    const disposers = new WeakMap(); // میزبان نمودار → تابع پاک‌سازی (چند نمودار هم‌زمان)

    function barChart(host, data, format, formatFull, emptyText) {
        if (disposers.has(host)) { disposers.get(host)(); disposers.delete(host); }
        host.innerHTML = "";
        if (!data.length) {
            host.innerHTML = `<div class="empty">${emptyText || "داده‌ای برای نمایش وجود ندارد."}</div>`;
            return;
        }

        const canvas = document.createElement("canvas");
        const renderer = makeRenderer(canvas);
        if (!renderer) { flatChart(host, data, format); return; }
        host.appendChild(canvas);

        const tip = document.createElement("div");
        tip.className = "tip";
        host.appendChild(tip);

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 100);

        scene.add(new THREE.AmbientLight(0xffffff, 0.75));
        const sun = new THREE.DirectionalLight(0xffffff, 0.9);
        sun.position.set(4, 8, 6);
        scene.add(sun);

        const stage = new THREE.Group();
        scene.add(stage);

        const STEP = 1.55;
        const MAX_H = 4;
        const max = Math.max(...data.map(d => d.value), 1);
        const width = (data.length - 1) * STEP;

        // کف نمودار
        const floor = new THREE.Mesh(
            new THREE.BoxGeometry(width + 2.4, 0.08, 2.4),
            new THREE.MeshStandardMaterial({ color: 0xe9ebf8, roughness: 0.9 })
        );
        floor.position.y = -0.04;
        stage.add(floor);

        const bars = data.map((d, i) => {
            const h = Math.max((d.value / max) * MAX_H, 0.06);
            const geo = new THREE.BoxGeometry(0.95, 1, 0.95);
            geo.translate(0, 0.5, 0); // پایهٔ میله روی y=0
            const last = i === data.length - 1;
            const mat = new THREE.MeshStandardMaterial({
                color: last ? 0x8b5cf6 : 0x6366f1,
                metalness: 0.15,
                roughness: 0.35,
            });
            const mesh = new THREE.Mesh(geo, mat);
            mesh.position.x = i * STEP - width / 2;
            mesh.scale.y = REDUCED ? h : 0.001;
            mesh.userData = { i, h, base: mat.color.getHex() };
            stage.add(mesh);
            return mesh;
        });

        // برچسب‌ها: عناصر HTML که هر فریم روی نقطهٔ سه‌بعدی نگاشت می‌شوند
        const labels = data.map((d, i) => {
            const month = document.createElement("div");
            month.className = "lbl";
            month.textContent = d.label;
            const val = document.createElement("div");
            val.className = "lbl val";
            val.textContent = format(d.value);
            host.append(month, val);
            return { month, val, x: bars[i].position.x, h: bars[i].userData.h };
        });

        const v = new THREE.Vector3();
        function place(el, x, y, z, w, h) {
            v.set(x, y, z).applyMatrix4(stage.matrixWorld).project(camera);
            el.style.transform = `translate(${(v.x * 0.5 + 0.5) * w}px, ${(-v.y * 0.5 + 0.5) * h}px) translate(-50%, -50%)`;
        }

        const pointer = { x: 0, y: 0, inside: false, cx: 0, cy: 0 };
        host.addEventListener("pointermove", e => {
            const r = host.getBoundingClientRect();
            pointer.cx = e.clientX - r.left;
            pointer.cy = e.clientY - r.top;
            pointer.x = (pointer.cx / r.width) * 2 - 1;
            pointer.y = -(pointer.cy / r.height) * 2 + 1;
            pointer.inside = true;
        });
        host.addEventListener("pointerleave", () => { pointer.inside = false; });

        const ray = new THREE.Raycaster();

        function resize() {
            fit(renderer, camera, host);
            // فاصلهٔ دوربین را طوری تنظیم می‌کنیم که همهٔ میله‌ها در کادر جا شوند
            const need = (width + 3) / (2 * Math.tan((camera.fov * Math.PI) / 360) * Math.max(camera.aspect, 0.4));
            const dist = Math.max(need, 11);
            camera.position.set(0, dist * 0.46, dist);
            camera.lookAt(0, MAX_H * 0.38, 0);
        }
        resize();
        const ro = new ResizeObserver(resize);
        ro.observe(host);

        const born = performance.now();
        let hovered = -1;

        const stop = loop(canvas, t => {
            const w = host.clientWidth, hh = host.clientHeight;
            const grow = REDUCED ? 1 : Math.min((performance.now() - born) / 900, 1);

            // حرکت آرام صحنه + کمی دنبال‌کردن اشاره‌گر
            const targetY = REDUCED ? 0 : Math.sin(t * 0.45) * 0.22 + (pointer.inside ? pointer.x * 0.3 : 0);
            stage.rotation.y += (targetY - stage.rotation.y) * 0.06;
            stage.rotation.x += ((pointer.inside ? -pointer.y * 0.06 : 0) - stage.rotation.x) * 0.06;
            stage.updateMatrixWorld(true);

            bars.forEach((b, i) => {
                const delay = i * 0.08;
                const p = Math.min(Math.max((grow - delay) / (1 - Math.min(delay, 0.5)), 0), 1);
                const eased = 1 - Math.pow(1 - p, 3);
                b.scale.y = Math.max(b.userData.h * eased, 0.001);
            });

            // hover
            let hit = -1;
            if (pointer.inside) {
                ray.setFromCamera(pointer, camera);
                const res = ray.intersectObjects(bars);
                if (res.length) hit = res[0].object.userData.i;
            }
            if (hit !== hovered) {
                if (hovered >= 0) bars[hovered].material.color.setHex(bars[hovered].userData.base);
                if (hit >= 0) bars[hit].material.color.offsetHSL(0, 0, 0.1);
                hovered = hit;
                host.style.cursor = hit >= 0 ? "pointer" : "";
            }
            if (hit >= 0) {
                tip.textContent = `${data[hit].tip}: ${formatFull(data[hit].value)}`;
                tip.style.left = pointer.cx + "px";
                tip.style.top = pointer.cy + "px";
                tip.classList.add("show");
            } else {
                tip.classList.remove("show");
            }

            labels.forEach((l, i) => {
                const hNow = bars[i].scale.y;
                place(l.month, l.x, 0, 1.45, w, hh);
                place(l.val, l.x, hNow + 0.4, 0, w, hh);
                l.val.style.opacity = grow >= 1 || REDUCED ? 1 : 0;
            });

            renderer.render(scene, camera);
        });

        disposers.set(host, () => {
            stop();
            ro.disconnect();
            renderer.dispose();
            scene.traverse(o => { if (o.geometry) o.geometry.dispose(); if (o.material) o.material.dispose(); });
        });
    }

    // نسخهٔ دوبعدی جایگزین (بدون WebGL)
    function flatChart(host, data, format) {
        const max = Math.max(...data.map(d => d.value), 1);
        host.innerHTML = '<div class="flat-bars">' + data.map(d =>
            `<div class="b"><span>${format(d.value)}</span><i style="height:${Math.max((d.value / max) * 75, 2)}%"></i>${d.label}</div>`
        ).join("") + "</div>";
    }

    window.Scenes = { background, barChart };
})();
