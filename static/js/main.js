/* TU SURE — main.js */

document.addEventListener('DOMContentLoaded', function () {

    // ================================================================
    // MOBILE MENU
    // ================================================================
    const hamburger = document.getElementById('hamburger');
    const mobileMenu = document.getElementById('mobile-menu');
    const header = document.getElementById('site-header');

    function openMenu() {
        mobileMenu.classList.add('open');
        hamburger.classList.add('active');
        hamburger.setAttribute('aria-expanded', 'true');
        mobileMenu.setAttribute('aria-hidden', 'false');
        document.body.classList.add('menu-open');
    }

    function closeMenu() {
        mobileMenu.classList.remove('open');
        hamburger.classList.remove('active');
        hamburger.setAttribute('aria-expanded', 'false');
        mobileMenu.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('menu-open');
    }

    function toggleMenu() {
        if (mobileMenu.classList.contains('open')) {
            closeMenu();
        } else {
            openMenu();
        }
    }

    if (hamburger && mobileMenu) {
        hamburger.addEventListener('click', function (e) {
            e.stopPropagation();
            toggleMenu();
        });

        // Close when a link inside the menu is clicked
        mobileMenu.querySelectorAll('a').forEach(function (link) {
            link.addEventListener('click', closeMenu);
        });

        // Close when clicking outside the menu
        document.addEventListener('click', function (e) {
            if (!mobileMenu.classList.contains('open')) return;
            if (header.contains(e.target)) return;
            closeMenu();
        });

        // Close on Escape key
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && mobileMenu.classList.contains('open')) {
                closeMenu();
                hamburger.focus();
            }
        });

        // Close when viewport resizes to desktop width
        let resizeTimer;
        window.addEventListener('resize', function () {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function () {
                if (window.innerWidth > 780) closeMenu();
            }, 150);
        });
    }

    // ================================================================
    // COPY-TO-CLIPBOARD FOR PREMIUM CODES
    // ================================================================
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.code-copy-btn');
        if (!btn) return;

        const value = btn.getAttribute('data-copy') || '';
        if (!value) return;

        const original = btn.innerHTML;

        function showSuccess() {
            btn.innerHTML = '✓ Copied';
            btn.classList.add('code-copy-success');
            setTimeout(function () {
                btn.innerHTML = original;
                btn.classList.remove('code-copy-success');
            }, 1800);
        }

        function showFail() {
            btn.innerHTML = 'Copy failed';
            setTimeout(function () { btn.innerHTML = original; }, 1800);
        }

        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(value).then(showSuccess).catch(showFail);
        } else {
            const ta = document.createElement('textarea');
            ta.value = value;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            try {
                document.execCommand('copy');
                showSuccess();
            } catch (err) {
                showFail();
            }
            document.body.removeChild(ta);
        }
    });

    // ================================================================
    // SCROLL REVEAL (subtle fade-in for sections)
    // ================================================================
    const reveals = document.querySelectorAll('.pick-card, .step-card, .record-card, .pricing-card, .faq-item');
    if ('IntersectionObserver' in window && reveals.length) {
        const observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.08, rootMargin: '0px 0px -60px 0px' });

        reveals.forEach(function (el) { observer.observe(el); });
    } else {
        // No IntersectionObserver — just reveal everything immediately
        reveals.forEach(function (el) { el.classList.add('revealed'); });
    }
        // ================================================================
    // LIVE RECORD TABLE — filter chips
    // ================================================================
    const liveTable = document.getElementById('live-record-table');
    if (liveTable) {
        const chips = document.querySelectorAll('.live-record-filters .chip');
        const rows = liveTable.querySelectorAll('.live-record-row');

        chips.forEach(function (chip) {
            chip.addEventListener('click', function () {
                const filter = chip.getAttribute('data-filter');

                chips.forEach(function (c) { c.classList.remove('chip-active'); });
                chip.classList.add('chip-active');

                rows.forEach(function (row) {
                    const result = row.getAttribute('data-result');
                    if (filter === 'all' || filter === result) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                });
            });
        });
    }

    console.log('2 SURE loaded.');
});