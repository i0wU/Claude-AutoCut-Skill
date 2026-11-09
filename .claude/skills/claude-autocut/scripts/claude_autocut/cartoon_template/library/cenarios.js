// Cenários do modo podcast-animado, em camadas de papel: fundo (parede com estampa, janela, estantes),
// meio (o que fica atrás dos personagens) e frente (mesa e objetos grandes na borda do quadro).
// Coordenadas lógicas do canvas de cima (1200 de largura); sobra papel dos lados para a câmera andar.
//   quarto   o quarto/estúdio do criador: janela de noite, ring light, quadro, estantes, mesa de madeira
//   sala     a sala de quem assiste: parede listrada, luminária, quadro, sofá
//   bancada  a mesa de trabalho da IA, de perto: quadro de cortiça, porta-lápis, base de corte
const Cenarios = (() => {
    const P = Paper, D = PaperDetail, E = Ease;
    const spr = (g, key, box, fn, res = 1.25) => Motion.sprite(key, box, Palco.env.k * res, fn).draw(g);
    const cut = (c, pts, col, seed, o = {}) => P.cutout(c, pts, col, seed, { border: 2.6, shadow: 0.18, ...o });
    const rect = (x, y, w, h) => [[x, y], [x + w, y], [x + w, y + h], [x, y + h]];

    // parede com estampa impressa (losangos pequenos) e textura de marcador; sem borda (é fundo)
    function parede(c, x, y, w, h, cor, semente, estampa = 'losango') {
        P.cutout(c, rect(x, y, w, h), cor, semente, { border: 0, shadow: 0, jag: 0.4, tex: { len: [60, 170], h: [12, 24], lVar: 3, alpha: [0.3, 0.6], density: 1.0 } });
        const r = P.rng(semente + ':est');
        c.save();
        c.globalAlpha = 0.22;
        c.fillStyle = D.shade(cor, 12);
        c.strokeStyle = D.shade(cor, 12);
        if (estampa === 'losango') {
            for (let yy = y + 20; yy < y + h; yy += 56) for (let xx = x + ((yy / 56) % 2 ? 28 : 0); xx < x + w; xx += 56) {
                c.save();
                c.translate(xx + (r() - 0.5) * 2, yy + (r() - 0.5) * 2);
                c.rotate(Math.PI / 4);
                c.fillRect(-5, -5, 10, 10);
                c.restore();
            }
        } else if (estampa === 'listras') {
            for (let xx = x; xx < x + w; xx += 64) P.markerStroke(c, [[xx, y], [xx + (r() - 0.5) * 3, y + h]], D.shade(cor, 10), 16, semente + xx, 0.9);
        }
        c.restore();
    }

    function livro(c, x, base, w, h, cor, semente, inclina = 0) {
        c.save();
        c.translate(x + w / 2, base);
        c.rotate(inclina);
        cut(c, rect(-w / 2, -h, w, h), cor, semente, { border: 2, tex: { alpha: [0.2, 0.4], angle: Math.PI / 2 } });
        c.fillStyle = D.shade(cor, 18);
        c.globalAlpha = 0.8;
        c.fillRect(-w / 2 + 3, -h * 0.78, w - 6, 5);
        c.fillRect(-w / 2 + 3, -h * 0.22, w - 6, 4);
        c.globalAlpha = 1;
        c.restore();
    }

    function planta(c, x, base, s, semente) {
        const r = P.rng(semente);
        c.save();
        c.translate(x, base);
        c.scale(s, s);
        for (let i = 0; i < 7; i++) {
            const a = -Math.PI / 2 + (i - 3) * 0.32 + (r() - 0.5) * 0.15, L = 70 + r() * 50;
            const ctrl = [[0, -20], [Math.cos(a) * L * 0.5, -20 + Math.sin(a) * L * 0.5], [Math.cos(a) * L, -20 + Math.sin(a) * L]];
            cut(c, D.taper(ctrl, [5, 22, 2], 6), i % 2 ? '#5fae7c' : '#4b9467', semente + 'f' + i, { border: 1.8, tex: { alpha: [0.18, 0.32] } });
        }
        cut(c, [[-34, -26], [34, -26], [26, 30], [-26, 30]], '#d06a45', semente + 'vaso', { inner: (cc) => { cc.fillStyle = D.shade('#d06a45', 10); cc.fillRect(-40, -26, 80, 12); } });
        c.restore();
    }

    function mesa(c, x0, x1, topo, frente, alt, semente) {
        // tampo em leve perspectiva (faixa) e a frente mais escura com gaveta
        cut(c, [[x0 + 30, topo], [x1 - 30, topo], [x1, frente], [x0, frente]], '#bf8a55', semente + 'tampo', { border: 2.4, tex: false, inner: (cc, box) => D.woodGrain(cc, box, '#bf8a55', { seed: semente + 'veio' }) });
        cut(c, rect(x0, frente, x1 - x0, alt), '#8e5d37', semente + 'frente', { border: 2.4, shadow: 0.25, tex: false, inner: (cc, box) => D.woodGrain(cc, box, '#8e5d37', { seed: semente + 'veio2' }) });
        P.markerStroke(c, [[x0 + 8, frente + 6], [x1 - 8, frente + 6]], '#6f4527', 5, semente + 'quina', 0.6);
    }

    // ------------------------------------------------------------------------------------- quarto
    const quarto = {
        fundo(g, t, p, ctx) {
            spr(g, 'quarto:parede', { x: -420, y: -300, w: 2040, h: 1220 }, (c) => {
                parede(c, -420, -300, 2040, 1220, '#4b2552', 'quarto-parede');
                // fita de LED rosa no alto da parede (o quarto do vídeo é iluminado de rosa)
                cut(c, rect(-420, 78, 2040, 22), '#e2489c', 'led', { border: 0, shadow: 0.12, tex: { alpha: [0.15, 0.3] } });
                cut(c, rect(-420, 85, 2040, 7), '#ff9fcf', 'led-nucleo', { border: 0, shadow: 0, tex: false });
                // janela de noite com a cidade
                cut(c, rect(14, 150, 236, 360), '#d9c3a2', 'jan-moldura', { border: 2.6 });
                cut(c, rect(30, 166, 204, 328), '#26305a', 'jan-ceu', { border: 0, shadow: 0.2, tex: { alpha: [0.2, 0.4] }, inner: (cc) => {
                    const r = P.rng('estrelas');
                    cc.fillStyle = '#f4ecda';
                    for (let i = 0; i < 22; i++) cc.fillRect(32 + r() * 200, 170 + r() * 150, 2.5, 2.5);
                } });
                cut(c, P.ellipse(184, 214, 26, 26, 48), '#f1e3c0', 'lua', { border: 1.8, inner: (cc) => { cc.fillStyle = '#ddcb9f'; for (const [x, y, rr] of [[176, 208, 5], [192, 222, 4], [186, 200, 3]]) (cc.beginPath(), cc.arc(x, y, rr, 0, 7), cc.fill()); } });
                const r = P.rng('predios');
                for (let i = 0; i < 6; i++) {
                    const bx = 30 + i * 34 + (r() - 0.5) * 6, bh = 90 + r() * 120, bw = 30 + r() * 16;
                    cut(c, rect(bx, 494 - bh, bw, bh), i % 2 ? '#1c2244' : '#232a52', 'predio' + i, { border: 0, shadow: 0.1, inner: (cc) => {
                        cc.fillStyle = '#f0c24f';
                        for (let yy = 494 - bh + 10; yy < 486; yy += 16) for (let xx = bx + 5; xx < bx + bw - 6; xx += 10) if (r() < 0.45) cc.fillRect(xx, yy, 5, 7);
                    } });
                }
                cut(c, rect(124, 166, 14, 328), '#d9c3a2', 'jan-cruz-v', { border: 1.4 });
                cut(c, rect(30, 318, 204, 12), '#d9c3a2', 'jan-cruz-h', { border: 1.4 });
                // cortina
                cut(c, D.spline([[2, 130], [70, 132], [64, 330], [80, 540], [-6, 546], [-10, 330]], 6), '#b25f7c', 'cortina', { inner: (cc) => { for (const x of [16, 34, 52]) P.markerStroke(cc, [[x, 140], [x - 4, 330], [x + 6, 540]], D.shade('#b25f7c', -10), 4, 'dobra' + x, 0.6); } });
                // quadro pequeno, calmo, acima e à direita da cabeça
                cut(c, rect(612, 168, 136, 170), '#e8dcc2', 'quadro', { inner: (cc) => {
                    cc.fillStyle = '#f2a541';
                    cc.beginPath(); cc.arc(680, 236, 26, 0, 7); cc.fill();
                    cc.fillStyle = '#3e8f86';
                    cc.beginPath(); cc.moveTo(626, 320); cc.lineTo(670, 260); cc.lineTo(700, 296); cc.lineTo(720, 276); cc.lineTo(736, 320); cc.fill();
                } });
                // estantes com livros, planta e porta-trecos
                for (const [y, x0, x1] of [[336, 790, 1190], [560, 960, 1210]]) {
                    cut(c, rect(x0, y, x1 - x0, 18), '#a8743f', 'prat' + y, { tex: false, inner: (cc, box) => D.woodGrain(cc, box, '#a8743f', { seed: 'prat' + y }) });
                }
                const cores = ['#e9b949', '#6cc9a1', '#f2643c', '#5b7fc4', '#d4d0c4', '#b98ad0', '#e07a5f', '#3f8f86'];
                let x = 806;
                cores.forEach((cor, i) => {
                    const w = 22 + (i * 7) % 14, h = 92 + (i * 23) % 40;
                    livro(c, x, 336, w, h, cor, 'livro' + i, i === 7 ? 0.22 : 0);
                    x += w + 3;
                });
                planta(c, 1110, 336, 0.85, 'planta-estante');
                for (let i = 0; i < 4; i++) livro(c, 1040, 560 - i * 16, 120 - i * 10, 16, ['#5b7fc4', '#f2643c', '#e9b949', '#6cc9a1'][i], 'pilha' + i, (i % 2 ? 0.02 : -0.02));
                livro(c, 1000, 560, 26, 70, '#d4d0c4', 'livro-baixo');
            });
            // ring light com pé, à esquerda do criador
            spr(g, 'quarto:ringlight', { x: 180, y: 300, w: 240, h: 620 }, (c) => {
                cut(c, P.roundRect(292, 520, 16, 380, 6), '#3a3644', 'rl-pe', { border: 2 });
                const anel = [...P.ellipse(300, 430, 96, 96, 80)];
                cut(c, anel, '#f6f0e1', 'rl-anel', { border: 2.4, shadow: 0.25 });
                c.fillStyle = '#4b2552';
                c.beginPath();
                c.arc(300, 430, 70, 0, Math.PI * 2);
                c.fill();
                P.cutout(c, P.ellipse(300, 430, 70, 70, 80), '#4b2552', 'rl-furo', { border: 0, shadow: 0, jag: 0.6, tex: { alpha: [0.3, 0.5], len: [40, 90], h: [10, 18] } });
                cut(c, P.roundRect(282, 520, 36, 30, 8), '#3a3644', 'rl-junta', { border: 1.8 });
            });
        },
        frente(g, t, p, ctx) {
            spr(g, 'quarto:mesa', { x: -420, y: 840, w: 2040, h: 300 }, (c) => {
                mesa(c, -420, 1620, 858, 902, 220, 'quarto-mesa');
                // caneca e caderno em cima da mesa
                cut(c, P.roundRect(352, 820, 54, 64, 10), '#6cc9a1', 'caneca', { inner: (cc) => { cc.fillStyle = '#f4ecda'; cc.fillRect(352, 836, 54, 8); } });
                cut(c, P.noodle(P.bezier([406, 834], [430, 836], [430, 868], [404, 870], 10), 9), '#6cc9a1', 'caneca-asa', { border: 1.8 });
                c.save();
                c.translate(700, 878);
                c.rotate(-0.06);
                cut(c, rect(-70, -26, 140, 40), '#f4eddd', 'caderno', { inner: (cc) => P.scribble(cc, -60, -14, 120, 2, 12, '#8b7f96', 'cad', { scale: 0.6 }) });
                cut(c, P.noodle([[-40, 0], [60, -18]], 7, 5), '#f2643c', 'caneta', { border: 1.4 });
                c.restore();
            });
        },
    };

    // ------------------------------------------------------------------------------------- sala
    const sala = {
        fundo(g, t, p, ctx) {
            spr(g, 'sala:fundo', { x: -420, y: -300, w: 2040, h: 1400 }, (c) => {
                parede(c, -420, -300, 2040, 1400, '#24444e', 'sala-parede', 'listras');
                // luminária de pé acesa
                cut(c, P.roundRect(178, 300, 12, 700, 5), '#2f2b36', 'lum-pe', { border: 2 });
                cut(c, [[120, 170], [250, 170], [290, 300], [80, 300]], '#e6a83b', 'lum-cupula', { inner: (cc) => { cc.fillStyle = '#f6d27a'; cc.fillRect(80, 284, 210, 16); } });
                cut(c, P.ellipse(184, 318, 56, 14, 40), '#f9e7a6', 'lum-luz', { border: 0, shadow: 0, tex: false });
                // dois quadros
                cut(c, rect(860, 150, 220, 160), '#efe4cc', 'sala-quadro1', { inner: (cc, box) => D.mapPaper(cc, { x: 876, y: 166, w: 188, h: 128 }, { seed: 'mapa' }) });
                cut(c, rect(990, 340, 120, 150), '#efe4cc', 'sala-quadro2', { inner: (cc) => { cc.fillStyle = '#e07a5f'; cc.beginPath(); cc.arc(1050, 410, 34, 0, 7); cc.fill(); } });
                planta(c, 1080, 720, 1.5, 'planta-sala');
            });
        },
        frente(g, t, p, ctx) {
            spr(g, 'sala:sofa', { x: -420, y: 600, w: 2040, h: 560 }, (c) => {
                // encosto com capitonê, braços nas pontas, almofadas de tricô
                cut(c, P.roundRect(-300, 690, 1800, 470, 60), '#c8664f', 'sofa', { inner: (cc, box) => {
                    D.knit(cc, box, '#c8664f', { seed: 'sofa', size: 16, alpha: 0.14 });
                    for (const x of [100, 360, 620, 880, 1140]) {
                        P.markerStroke(cc, [[x, 720], [x, 900]], D.shade('#c8664f', -9), 4, 'costura' + x, 0.6);
                        cc.fillStyle = D.shade('#c8664f', -14);
                        cc.beginPath();
                        cc.arc(x + 130, 800, 6, 0, 7);
                        cc.fill();
                    }
                } });
                for (const x of [-120, 1220]) cut(c, P.roundRect(x, 640, 140, 520, 60), D.shade('#c8664f', -6), 'braco-sofa' + x, { inner: (cc, box) => D.knit(cc, box, '#b9573f', { seed: 'bs' + x, size: 16, alpha: 0.14 }) });
                for (const [x, cor, r] of [[40, '#e9b949', -0.12], [960, '#6cc9a1', 0.1]]) {
                    c.save();
                    c.translate(x + 90, 800);
                    c.rotate(r);
                    cut(c, D.spline([[-90, -80], [90, -86], [100, 76], [-96, 84]], 6), cor, 'almofada' + x, { inner: (cc, box) => D.knit(cc, box, cor, { seed: 'alm' + x, size: 12, alpha: 0.16 }) });
                    c.restore();
                }
            });
        },
    };

    // ------------------------------------------------------------------------------------- bancada
    const bancada = {
        fundo(g, t, p, ctx) {
            spr(g, 'bancada:fundo', { x: -420, y: -300, w: 2040, h: 1500 }, (c) => {
                parede(c, -420, -300, 2040, 900, '#4b2552', 'bancada-parede');
                cut(c, rect(-420, 40, 2040, 18), '#e2489c', 'led2', { border: 0, shadow: 0.12, tex: { alpha: [0.15, 0.3] } });
                // quadro de cortiça com bilhetes presos, à direita (o notebook fica à esquerda)
                cut(c, rect(640, 110, 500, 330), '#c79a63', 'cortica', { inner: (cc) => {
                    const r = P.rng('cortica-pontos');
                    cc.fillStyle = '#9c7444';
                    for (let i = 0; i < 420; i++) cc.fillRect(642 + r() * 496, 112 + r() * 326, 2.4, 2.4);
                } });
                const notas = [[670, 140, '#f6d365', -0.05], [810, 132, '#9fe0c9', 0.04], [960, 146, '#f5a8c5', -0.03], [700, 290, '#f5a8c5', 0.05], [870, 292, '#f6d365', -0.04], [1010, 300, '#9fe0c9', 0.03]];
                notas.forEach(([x, y, cor, rr], i) => {
                    c.save();
                    c.translate(x + 55, y + 55);
                    c.rotate(rr);
                    cut(c, rect(-55, -55, 110, 110), cor, 'nota' + i, { border: 2, inner: (cc) => P.scribble(cc, -44, -26, 88, 4, 18, '#6d5a78', 'nota-esc' + i, { scale: 0.8 }) });
                    cut(c, P.ellipse(0, -44, 7, 7, 20), ['#f2643c', '#5b7fc4', '#e9b949'][i % 3], 'alfinete' + i, { border: 1.4, shadow: 0.3 });
                    c.restore();
                });
                // prateleira alta com livros, à esquerda, acima do notebook
                cut(c, rect(-60, 210, 420, 18), '#a8743f', 'prat-banc', { tex: false, inner: (cc, box) => D.woodGrain(cc, box, '#a8743f', { seed: 'prat-banc' }) });
                ['#e9b949', '#6cc9a1', '#f2643c', '#5b7fc4', '#d4d0c4', '#b98ad0'].forEach((cor, i) => livro(c, -20 + i * 30, 210, 26, 84 + (i * 17) % 30, cor, 'banc-livro' + i, i === 5 ? 0.25 : 0));
                planta(c, 300, 210, 0.75, 'planta-prat');
                // tampo grande visto de perto e a base de corte verde quadriculada
                cut(c, rect(-420, 600, 2040, 760), '#bf8a55', 'bancada-tampo', { border: 0, shadow: 0, tex: false, inner: (cc, box) => D.woodGrain(cc, box, '#bf8a55', { seed: 'bancada-veio' }) });
                P.markerStroke(c, [[-420, 604], [1620, 604]], '#8e5d37', 6, 'tampo-quina', 0.7);
                cut(c, [[40, 660], [1160, 660], [1190, 1040], [10, 1040]], '#3f8f6f', 'base-corte', { border: 2.6, inner: (cc) => {
                    cc.strokeStyle = 'rgba(214,240,226,0.45)';
                    cc.lineWidth = 1.4;
                    for (let x = 60; x < 1180; x += 40) (cc.beginPath(), cc.moveTo(x, 660), cc.lineTo(x + (x - 600) * 0.03, 1040), cc.stroke());
                    for (let y = 680; y < 1040; y += 40) (cc.beginPath(), cc.moveTo(20, y), cc.lineTo(1180, y), cc.stroke());
                    cc.strokeStyle = 'rgba(244,236,218,0.8)';
                    cc.lineWidth = 2;
                    for (let x = 60; x < 1180; x += 20) (cc.beginPath(), cc.moveTo(x, 664), cc.lineTo(x, x % 100 === 60 ? 680 : 672), cc.stroke());
                } });
                // régua, lápis, borracha e retalhos em cima da base
                c.save();
                c.translate(220, 712);
                c.rotate(-0.05);
                cut(c, rect(-150, -16, 300, 32), '#f2d16b', 'regua', { border: 2.2, inner: (cc) => {
                    cc.fillStyle = '#7a5a2a';
                    for (let x = -144; x < 150; x += 10) cc.fillRect(x, -16, 1.6, x % 50 === 6 ? 14 : 8);
                } });
                c.restore();
                c.save();
                c.translate(860, 716);
                c.rotate(0.12);
                cut(c, P.noodle([[-110, 0], [90, 0]], 14, 13), '#f2643c', 'lapis-base', { border: 1.8 });
                cut(c, [[90, -7], [126, 0], [90, 7]], '#f0d2a8', 'lapis-ponta', { border: 1.4 });
                cut(c, P.roundRect(-140, -9, 32, 18, 5), '#f5a8c5', 'lapis-borracha', { border: 1.4 });
                c.restore();
                cut(c, P.roundRect(1010, 696, 70, 40, 8), '#f5a8c5', 'borracha', { inner: (cc) => { cc.fillStyle = '#5b7fc4'; cc.fillRect(1010, 696, 30, 40); } });
                const rr = P.rng('retalhos');
                for (let i = 0; i < 5; i++) {
                    const x = 80 + rr() * 1040, y = 960 + rr() * 50, s = 12 + rr() * 14;
                    cut(c, [[x - s, y - s * 0.6], [x + s, y - s * 0.4], [x + s * 0.7, y + s * 0.7], [x - s * 0.8, y + s * 0.5]], ['#f4ecda', '#f6d365', '#9fe0c9'][i % 3], 'retalho' + i, { border: 1.6 });
                }
                // porta-lápis entre o notebook e a cortiça (lápis atrás do copo)
                for (const [x, cor, h] of [[528, '#f2643c', 120], [550, '#e9b949', 140], [572, '#6cc9a1', 110]]) cut(c, P.roundRect(x, 610 - h + 20, 12, h, 4), cor, 'lapis' + x, { border: 1.6 });
                cut(c, P.roundRect(510, 520, 90, 110, 12), '#5b7fc4', 'porta-lapis', { inner: (cc, box) => D.rib(cc, box, '#5b7fc4', { step: 14, width: 4, angle: Math.PI / 2 }) });
                planta(c, 1150, 610, 1.1, 'planta-bancada');
            });
        },
    };

    Palco.cenario('quarto', quarto);
    Palco.cenario('sala', sala);
    Palco.cenario('bancada', bancada);
    return { quarto, sala, bancada, parede, livro, planta, mesa };
})();
