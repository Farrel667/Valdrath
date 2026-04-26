/**
 * game.js — Valdrath: The Veil v2.1
 *
 * ROOT BUG FIX: Setting button.disabled = true synchronously inside a click
 * handler cancels the form submission in all modern browsers. We now use a
 * CSS "pending" class for visual feedback and only disable after the form
 * has already started submitting (via the 'submit' event).
 */

// ═══════════════════════════════════════════════════════════════════════════
// VFX ENGINE
// ═══════════════════════════════════════════════════════════════════════════

const VFX = {

    overlay:   document.getElementById('vfx-overlay'),
    particles: document.getElementById('vfx-particles'),
    popup:     document.getElementById('vfx-popup'),

    presets: {
        attack: {
            flashAlpha: 0.08, particleCount: 14, particleSize: [4,9],
            particleDur: [0.5,0.8], particleRange: 200, streakCount: 4, shake: 'sm',
        },
        defend: {
            flashAlpha: 0.06, particleCount: 10, particleSize: [3,7],
            particleDur: [0.4,0.7], particleRange: 160, streakCount: 0, shake: null,
        },
        slash: {
            flashAlpha: 0.14, particleCount: 22, particleSize: [3,8],
            particleDur: [0.5,0.9], particleRange: 280, streakCount: 8,
            streakWidth: [30,90], streakHeight: [2,4], shake: 'sm',
        },
        dragon: {
            flashAlpha: 0.22, particleCount: 40, particleSize: [4,12],
            particleDur: [0.6,1.2], particleRange: 380, streakCount: 10,
            streakWidth: [20,70], streakHeight: [2,5], shake: 'lg',
        },
        impact: {
            flashAlpha: 0.18, particleCount: 28, particleSize: [5,14],
            particleDur: [0.55,1.0], particleRange: 320, streakCount: 6,
            streakWidth: [20,60], streakHeight: [3,6], shake: 'lg', rings: true,
        },
        quake: {
            flashAlpha: 0.25, particleCount: 50, particleSize: [5,15],
            particleDur: [0.7,1.4], particleRange: 420, streakCount: 12,
            streakWidth: [15,50], streakHeight: [3,7], shake: 'lg', quakeMode: true,
        },
        fire: {
            flashAlpha: 0.20, particleCount: 35, particleSize: [4,11],
            particleDur: [0.5,1.1], particleRange: 340, streakCount: 8,
            streakWidth: [25,65], streakHeight: [2,5], shake: 'sm', fireMode: true,
        },
        void: {
            flashAlpha: 0.30, particleCount: 55, particleSize: [3,13],
            particleDur: [0.8,1.5], particleRange: 460, streakCount: 14,
            streakWidth: [10,55], streakHeight: [2,6], shake: 'lg', voidMode: true,
        },
    },

    rnd(a, b)    { return a + Math.random() * (b - a); },
    rndInt(a, b) { return Math.floor(this.rnd(a, b + 1)); },

    flash(color, alpha) {
        if (!this.overlay) return;
        this.overlay.style.background = color;
        this.overlay.style.opacity    = alpha;
        this.overlay.classList.remove('vfx-flash');
        void this.overlay.offsetWidth;
        this.overlay.classList.add('vfx-flash');
    },

    showPopup(icon, name, color) {
        if (!this.popup) return;
        this.popup.textContent = `${icon} ${name}`;
        this.popup.style.color = color;
        this.popup.classList.remove('vfx-popup-show');
        void this.popup.offsetWidth;
        this.popup.classList.add('vfx-popup-show');
        setTimeout(() => this.popup.classList.remove('vfx-popup-show'), 900);
    },

    shake(type) {
        const panel = document.querySelector('.narrative-panel');
        if (!panel || !type) return;
        const cls = type === 'lg' ? 'vfx-shake-lg' : 'vfx-shake-sm';
        panel.classList.remove('vfx-shake-sm', 'vfx-shake-lg');
        void panel.offsetWidth;
        panel.classList.add(cls);
        setTimeout(() => panel.classList.remove(cls), 600);
    },

    arenaGlow(color) {
        const arena = document.getElementById('combat-arena');
        if (!arena || !color.startsWith('#')) return;
        const r = parseInt(color.slice(1,3),16);
        const g = parseInt(color.slice(3,5),16);
        const b = parseInt(color.slice(5,7),16);
        arena.style.setProperty('--glow-col', `rgba(${r},${g},${b},0.5)`);
        arena.classList.remove('vfx-arena-glow');
        void arena.offsetWidth;
        arena.classList.add('vfx-arena-glow');
        setTimeout(() => arena.classList.remove('vfx-arena-glow'), 900);
    },

    hitEntity(id) {
        const el = document.getElementById(id);
        if (!el) return;
        el.classList.remove('entity-hit');
        void el.offsetWidth;
        el.classList.add('entity-hit');
        setTimeout(() => el.classList.remove('entity-hit'), 500);
    },

    burst(ox, oy, preset, color) {
        if (!this.particles) return;
        const p = this.presets[preset] || this.presets.attack;

        for (let i = 0; i < p.particleCount; i++) {
            const el   = document.createElement('div');
            el.className = 'vfx-p';
            const size = this.rnd(...p.particleSize);
            const dur  = this.rnd(...p.particleDur);
            const ang  = this.rnd(0, Math.PI * 2);
            const dist = this.rnd(40, p.particleRange);
            let tx = Math.cos(ang) * dist;
            let ty = Math.sin(ang) * dist;
            if (p.quakeMode) { ty = -Math.abs(ty) - this.rnd(30,180); tx = this.rnd(-p.particleRange*0.5, p.particleRange*0.5); }
            if (p.fireMode)  { ty -= this.rnd(60,160); }
            if (p.voidMode && i > p.particleCount * 0.4) { const s = this.rnd(1.2,1.8); tx*=s; ty*=s; }
            el.style.cssText = `left:${ox}px;top:${oy}px;width:${size}px;height:${size}px;background:${color};box-shadow:0 0 ${size*1.5}px ${color};--tx:${tx}px;--ty:${ty}px;--dur:${dur}s;animation-duration:${dur}s;`;
            this.particles.appendChild(el);
            setTimeout(() => el.remove(), dur * 1000 + 50);
        }

        if (p.streakCount) {
            for (let i = 0; i < p.streakCount; i++) {
                const el  = document.createElement('div');
                el.className = 'vfx-streak';
                const w   = this.rnd(...(p.streakWidth  || [20,80]));
                const h   = this.rnd(...(p.streakHeight || [2,5]));
                const ang = this.rnd(-30, 30);
                const dur = this.rnd(0.3, 0.6);
                el.style.cssText = `left:${ox+this.rnd(-60,60)}px;top:${oy+this.rnd(-20,20)}px;width:${w}px;height:${h}px;background:linear-gradient(90deg,${color},transparent);opacity:0.8;transform:rotate(${ang}deg);box-shadow:0 0 6px ${color};animation-duration:${dur}s;`;
                this.particles.appendChild(el);
                setTimeout(() => el.remove(), dur*1000+50);
            }
        }

        if (p.rings) {
            for (let i = 0; i < 3; i++) {
                const ring = document.createElement('div');
                const delay = i * 80;
                ring.style.cssText = `position:absolute;left:${ox}px;top:${oy}px;width:10px;height:10px;border:2px solid ${color};border-radius:50%;transform:translate(-50%,-50%);box-shadow:0 0 10px ${color};animation:ring-expand 0.6s ease-out ${delay}ms forwards;`;
                this.particles.appendChild(ring);
                setTimeout(() => ring.remove(), 700 + delay);
            }
            if (!document.getElementById('vfx-ring-style')) {
                const s = document.createElement('style');
                s.id = 'vfx-ring-style';
                s.textContent = `@keyframes ring-expand{0%{width:10px;height:10px;opacity:1}100%{width:180px;height:180px;opacity:0}}`;
                document.head.appendChild(s);
            }
        }
    },

    getOrigin(id) {
        const el = document.getElementById(id);
        if (!el) return { x: window.innerWidth * 0.62, y: window.innerHeight * 0.35 };
        const r = el.getBoundingClientRect();
        return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    },

    fire(vfxType, color, icon, name) {
        const p = this.presets[vfxType] || this.presets.attack;
        const o = this.getOrigin('entity-enemy');
        this.flash(color, p.flashAlpha);
        this.burst(o.x, o.y, vfxType, color);
        if (name && name !== 'Strike' && name !== 'Guard') {
            this.showPopup(icon || '✦', name, color);
        }
        this.shake(p.shake);
        this.arenaGlow(color);
        setTimeout(() => this.hitEntity('entity-enemy'), 80);
    },

    aftermath(vfxData) {
        if (!vfxData || !vfxData.color.startsWith('#')) return;
        const arena = document.getElementById('combat-arena');
        if (!arena) return;
        const r = parseInt(vfxData.color.slice(1,3),16);
        const g = parseInt(vfxData.color.slice(3,5),16);
        const b = parseInt(vfxData.color.slice(5,7),16);
        arena.style.setProperty('--aftermath-col', `rgba(${r},${g},${b},0.45)`);
        arena.classList.remove('arena-aftermath');
        void arena.offsetWidth;
        arena.classList.add('arena-aftermath');
        const log = document.getElementById('combat-log');
        if (log) {
            const last = log.querySelector('.log-entry:last-child');
            if (last) {
                last.style.cssText = `transition:background 0.4s;background:rgba(${r},${g},${b},0.08);border-radius:4px;padding:2px 4px;`;
                setTimeout(() => { last.style.background = 'transparent'; }, 1500);
            }
        }
    },
};

// ═══════════════════════════════════════════════════════════════════════════
// COMBAT BUTTON HOOKS
//
// ⚠ THE FIX: We NEVER call btn.disabled = true inside a click handler.
//   Disabling a submit button synchronously in its click event cancels the
//   form submission in Chrome, Firefox and Edge. Instead we:
//   1. Fire VFX on click (no disabling here)
//   2. On the form's 'submit' event, set pointer-events:none + opacity on the
//      entire actions area so the user can't resubmit, WITHOUT actually
//      disabling any element (which would kill in-flight submissions).
// ═══════════════════════════════════════════════════════════════════════════

// Pull skill icon/name into data attributes before anything else
document.querySelectorAll('.btn--skill[data-vfx]').forEach(btn => {
    const iconEl = btn.querySelector('.skill-icon');
    const nameEl = btn.querySelector('.skill-name-text');
    if (iconEl) btn.dataset.icon  = iconEl.textContent.trim();
    if (nameEl) btn.dataset.label = nameEl.textContent.trim();
});

// VFX fires on mousedown (earlier than click = snappier feel)
// but we DON'T modify disabled state here at all
document.querySelectorAll('[data-vfx]:not([disabled])').forEach(btn => {
    btn.addEventListener('mousedown', function() {
        const vfxType = this.dataset.vfx    || 'attack';
        const color   = this.dataset.color  || '#f0ead8';
        const icon    = this.dataset.icon   || '✦';
        const label   = this.dataset.label  || '';
        VFX.fire(vfxType, color, icon, label);
    });
});

// Form submit: lock the WHOLE action area visually (no disabled changes)
document.querySelectorAll('.combat-form, .skill-form, .choice-form').forEach(form => {
    form.addEventListener('submit', function() {
        // Lock combat actions area so the user can't spam while server processes
        const actionsArea = document.querySelector('.combat-actions');
        const skillsArea  = document.querySelector('.skills-grid');
        [actionsArea, skillsArea].forEach(el => {
            if (el) {
                el.style.pointerEvents = 'none';
                el.style.opacity = '0.5';
                el.style.transition = 'opacity 0.15s';
            }
        });
        // Also dim just the submitted button for visual feedback
        const btn = this.querySelector('button[type="submit"]');
        if (btn) {
            btn.style.transform = 'scale(0.96)';
            btn.style.filter    = 'brightness(0.7)';
        }
    });
});

// ═══════════════════════════════════════════════════════════════════════════
// HP BAR ANIMATIONS
// ═══════════════════════════════════════════════════════════════════════════

(function() {
    document.querySelectorAll('.hud__bar, .entity-hp-fill, .stat-bar').forEach(b => {
        const w = b.style.width;
        b.style.width = '0';
        requestAnimationFrame(() => requestAnimationFrame(() => {
            b.style.transition = 'width 1s cubic-bezier(0.4,0,0.2,1)';
            b.style.width = w;
        }));
    });
    // Pulse player entity when critical
    const fill = document.getElementById('player-hp-fill');
    if (fill && parseFloat(fill.style.width) <= 25) {
        document.getElementById('entity-player')?.classList.add('entity--critical');
    }
})();

// ═══════════════════════════════════════════════════════════════════════════
// NARRATIVE TEXT STAGGERED REVEAL
// ═══════════════════════════════════════════════════════════════════════════

(function() {
    const el = document.getElementById('narrative-text');
    if (!el) return;
    el.querySelectorAll('p, h1, h2, h3, hr').forEach((p, i) => {
        p.style.opacity    = '0';
        p.style.transform  = 'translateY(12px)';
        p.style.transition = `opacity 0.5s ease ${150+i*110}ms, transform 0.5s ease ${150+i*110}ms`;
        requestAnimationFrame(() => requestAnimationFrame(() => {
            p.style.opacity   = '1';
            p.style.transform = 'translateY(0)';
        }));
    });
})();

// ═══════════════════════════════════════════════════════════════════════════
// COMBAT LOG — stagger entries + scroll into view
// ═══════════════════════════════════════════════════════════════════════════

(function() {
    const log = document.getElementById('combat-log');
    if (!log) return;
    log.querySelectorAll('.log-entry').forEach((entry, i) => {
        entry.style.opacity   = '0';
        entry.style.transform = 'translateX(-8px)';
        entry.style.transition = `opacity 0.3s ease ${i*80}ms, transform 0.3s ease ${i*80}ms`;
        requestAnimationFrame(() => requestAnimationFrame(() => {
            entry.style.opacity   = '1';
            entry.style.transform = 'translateX(0)';
        }));
    });
    setTimeout(() => log.scrollIntoView({ behavior:'smooth', block:'nearest' }), 300);
})();

// ═══════════════════════════════════════════════════════════════════════════
// PLAY AFTERMATH VFX ON PAGE LOAD (after server redirect)
// ═══════════════════════════════════════════════════════════════════════════

if (window.LAST_VFX) {
    setTimeout(() => VFX.aftermath(window.LAST_VFX), 200);
}

// ═══════════════════════════════════════════════════════════════════════════
// FLASH MESSAGE AUTO-DISMISS
// ═══════════════════════════════════════════════════════════════════════════

document.querySelectorAll('.flash').forEach((el, i) => {
    setTimeout(() => {
        el.style.transition = 'opacity 0.4s, transform 0.4s';
        el.style.opacity    = '0';
        el.style.transform  = 'translateX(20px)';
        setTimeout(() => el.remove(), 400);
    }, 4800 + i * 300);
});

// ═══════════════════════════════════════════════════════════════════════════
// SKILL BUTTON DYNAMIC GLOW ON HOVER
// ═══════════════════════════════════════════════════════════════════════════

document.querySelectorAll('.btn--skill:not([disabled])').forEach(btn => {
    const color = getComputedStyle(btn).getPropertyValue('--skill-col').trim();
    if (!color) return;
    btn.addEventListener('mouseenter', () => {
        btn.style.boxShadow = `0 8px 32px rgba(0,0,0,0.5), 0 0 24px ${color}44`;
    });
    btn.addEventListener('mouseleave', () => {
        btn.style.boxShadow = '';
    });
});
