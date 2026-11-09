// Objetos do modo podcast-animado, em papel recortado. Cada um é desenhado com a origem no próprio
// centro (ou na base, quando fica em cima de algo). O palco já aplicou posição, giro, escala e o
// efeito de entrada; aqui o objeto só pinta o seu estado no tempo t. Global: Objetos.
//
// No storyboard: { tipo, x, y, s, rot, entra, sai, efeito: pop|cai|sobe|desliza_esq|desliza_dir|aparece|nenhum,
//                  sai_efeito: 'cai', camada: fundo|meio|frente, ...parâmetros do tipo }
const Objetos = (() => {
    const P = Paper, D = PaperDetail, E = Ease;
    const spr = (g, key, box, fn, res = 1.7) => Motion.sprite(key, box, Palco.env.k * res, fn).draw(g);
    const cut = (c, pts, col, seed, o = {}) => P.cutout(c, pts, col, seed, { border: 2.6, shadow: 0.2, ...o });
    const rect = (x, y, w, h) => [[x, y], [x + w, y], [x + w, y + h], [x, y + h]];
    const ob = Palco.objeto;

    // celular no tripé, visto por trás, gravando (luz vermelha pisca)
    ob('celular_tripe', (g, t, o) => {
        spr(g, 'tripe', { x: -130, y: -380, w: 260, h: 400 }, (c) => {
            for (const [a, b, s] of [[[0, -150], [-110, 10], 'p1'], [[0, -150], [110, 10], 'p2'], [[0, -150], [10, 14], 'p3']]) cut(c, P.noodle([a, b], 12, 9), '#3a3644', 'tripe' + s, { border: 2 });
            cut(c, P.roundRect(-14, -200, 28, 64, 6), '#2f2b36', 'tripe-coluna', { border: 2 });
            cut(c, P.roundRect(-30, -214, 60, 22, 6), '#2f2b36', 'tripe-cabeca', { border: 2 });
            cut(c, P.roundRect(-92, -366, 184, 156, 22), '#2c2833', 'cel-costas', { shadow: 0.28 });
            cut(c, P.roundRect(-74, -350, 64, 70, 16), '#3b3746', 'cel-camera', { border: 2 });
            for (const [x, y] of [[-56, -332], [-28, -332], [-56, -300]]) cut(c, P.ellipse(x, y, 11, 11, 24), '#14121a', 'lente' + x + y, { border: 2, shadow: 0.1, inner: (cc) => { cc.fillStyle = '#5a6a8a'; cc.beginPath(); cc.arc(x - 3, y - 3, 3.5, 0, 7); cc.fill(); } });
        });
        if (o.rec !== false && Math.floor(t * 2) % 2 === 0) {
            spr(g, 'rec-luz', { x: 20, y: -350, w: 70, h: 40 }, (c) => cut(c, P.ellipse(40, -330, 10, 10, 24), '#ff4b3e', 'rec', { border: 2 }));
        }
        Texto.etiqueta(g, 'REC', 64, -332, { tam: 26, rot: 0.06, cor: '#fbf3df', tinta: '#c9412f' });
    });

    // balão de fala com texto à mão; risca(t) cruza o texto em vermelho
    ob('balao', (g, t, o) => {
        const kit = Palco.kit, tam = o.tam ?? 44;
        g.font = `${tam}px "Hand"`;
        const w = Math.max(160, kit.textW(g, o.txt, tam) + 70), h = tam * 2.1;
        const cauda = o.cauda ?? 'esq';
        spr(g, 'balao:' + o.txt + cauda + tam, { x: -w / 2 - 50, y: -h / 2 - 20, w: w + 100, h: h + 90 }, (c) => {
            const corpo = P.circleUnion([[0, 0, h * 0.62], [-w * 0.3, 4, h * 0.5], [w * 0.3, 4, h * 0.5], [-w * 0.15, -6, h * 0.55], [w * 0.15, -4, h * 0.55]]);
            const cx = cauda === 'esq' ? -w * 0.22 : cauda === 'dir' ? w * 0.22 : 0;
            const ponta = cauda === 'esq' ? [-w * 0.42, h * 0.95] : cauda === 'dir' ? [w * 0.42, h * 0.95] : [0, h * 1.05];
            cut(c, [[cx - 22, h * 0.25], ponta, [cx + 18, h * 0.3]], o.cor ?? '#fbf7ee', 'cauda' + o.txt, { border: 2.4 });
            cut(c, corpo, o.cor ?? '#fbf7ee', 'balao' + o.txt, { border: 2.6 });
        });
        kit.hand(g, o.txt, 0, tam * 0.32, tam, o.tinta ?? '#33306e', { align: 'center', p: Math.min(1, (o.u ?? 1) * 1.4) });
        if (o.risca != null && t >= o.risca) {
            const u = E.seg(t, o.risca, o.risca + 0.25);
            const L = kit.textW(g, o.txt, tam) * 0.6 + 20;
            P.markerStroke(g, [[-L, -8], [-L + 2 * L * u, -2 + 10 * u]], '#e0402e', 7, 'risca' + o.txt, 0.95);
        }
    });

    // pergunta: selo amarelo com «?»
    ob('interrogacao', (g, t, o) => {
        const bal = Math.sin(t * 3) * 0.06;
        g.rotate(bal);
        spr(g, 'interrogacao', { x: -70, y: -70, w: 140, h: 140 }, (c) => {
            cut(c, P.circleUnion([[0, 0, 52], [18, -14, 40], [-16, 14, 40]]), '#ffd23f', 'interrog', { border: 3 });
            c.font = '92px "Anton"';
            c.textAlign = 'center';
            c.fillStyle = '#2a1826';
            c.fillText('?', 2, 32);
        });
    });

    // lixeira de tela de arame, com papéis amassados dentro (o.cheia = 0..1)
    ob('lixeira', (g, t, o) => {
        const cheia = o.cheia ?? 0;
        spr(g, 'lixeira-fundo', { x: -110, y: -170, w: 220, h: 190 }, (c) => cut(c, P.ellipse(0, -150, 92, 16, 48), '#3c4b55', 'lix-boca', { border: 2.2, shadow: 0 }));
        if (cheia > 0) for (let i = 0; i < Math.ceil(cheia * 4); i++) desenharBola(g, -50 + i * 30, -150 - (i % 2) * 10, 0.55, 'lixo' + i);
        spr(g, 'lixeira', { x: -110, y: -170, w: 220, h: 200 }, (c) => {
            cut(c, [[-92, -150], [92, -150], [70, 10], [-70, 10]], '#5d7480', 'lix-corpo', { inner: (cc) => {
                cc.strokeStyle = 'rgba(30,42,50,0.55)';
                cc.lineWidth = 2;
                for (let x = -84; x <= 84; x += 14) (cc.beginPath(), cc.moveTo(x, -150), cc.lineTo(x * 0.76, 10), cc.stroke());
                for (let y = -130; y < 10; y += 26) (cc.beginPath(), cc.moveTo(-92, y), cc.lineTo(92, y), cc.stroke());
            } });
            cut(c, P.noodle(P.ellipse(0, -150, 92, 16, 48).concat([[92, -150]]), 9), '#7f97a3', 'lix-aro', { border: 1.8, shadow: 0.15 });
        });
    });

    function desenharBola(g, x, y, s, semente) {
        g.save();
        g.translate(x, y);
        g.scale(s, s);
        spr(g, 'bola:' + semente, { x: -60, y: -60, w: 120, h: 120 }, (c) => {
            const r = P.rng(semente);
            const circ = Array.from({ length: 7 }, () => [(r() - 0.5) * 34, (r() - 0.5) * 34, 22 + r() * 10]);
            cut(c, P.circleUnion(circ), '#f4ecda', semente, { border: 2.2, inner: () => {
                for (let i = 0; i < 6; i++) {
                    const a = r() * 6.28, b = a + 1 + r();
                    P.markerStroke(c, [[Math.cos(a) * 30, Math.sin(a) * 30], [(r() - 0.5) * 10, (r() - 0.5) * 10], [Math.cos(b) * 28, Math.sin(b) * 28]], '#cbbfa6', 2.2, semente + 'v' + i, 0.7);
                }
            } });
        });
        g.restore();
    }
    ob('bola_papel', (g, t, o) => desenharBola(g, 0, 0, 1, o.semente ?? 'bola'));

    // ficha de palavra: etiqueta de papel com a palavra escrita à mão
    function ficha(g, txt, o = {}) {
        const kit = Palco.kit, tam = o.tam ?? 40;
        g.font = `${tam}px "Hand"`;
        const w = Math.max(70, kit.textW(g, txt, tam) + 34), h = tam * 1.5;
        const cor = o.cor ?? '#fbf3df';
        spr(g, 'ficha:' + txt + cor + tam, { x: -w / 2 - 10, y: -h / 2 - 10, w: w + 20, h: h + 22 }, (c) => {
            cut(c, P.roundRect(-w / 2, -h / 2, w, h, 8), cor, 'ficha' + txt + cor, { border: 2.4, tex: { alpha: [0.12, 0.25] } });
            c.fillStyle = 'rgba(42,24,38,0.18)';
            c.beginPath();
            c.arc(-w / 2 + 12, 0, 4, 0, 7);
            c.fill();
        });
        if (txt.trim()) kit.hand(g, txt, 4, tam * 0.33, tam, o.tinta ?? '#33306e', { align: 'center' });
        return w;
    }
    ob('ficha', (g, t, o) => ficha(g, o.txt, o));

    // círculo de marcador vermelho que se desenha (o.u de 0 a 1 com a entrada)
    function circulo(g, rx, ry, u, semente, cor = '#e0402e', larg = 6) {
        if (u <= 0) return;
        const pts = [];
        const n = 48, volta = 1.12;
        for (let i = 0; i <= n * u; i++) {
            const a = -2.2 + (i / n) * Math.PI * 2 * volta;
            const w = 1 + Motion.noise1(semente, i * 0.3) * 0.05;
            pts.push([Math.cos(a) * rx * w, Math.sin(a) * ry * w]);
        }
        if (pts.length > 1) P.markerStroke(g, pts, cor, larg, semente, 0.95);
    }
    ob('circulo', (g, t, o) => circulo(g, o.rx ?? 80, o.ry ?? 44, o.u ?? 1, 'circ' + (o.semente ?? o.x)));

    // tesoura: duas lâminas e cabos laranja; abre (0..1)
    function tesoura(g, abre, semente = 'tes') {
        const a = 0.08 + abre * 0.42;
        for (const sd of [-1, 1]) {
            g.save();
            g.rotate(sd * a);
            spr(g, 'tes-lamina' + sd, { x: -30, y: -30, w: 240, h: 60 }, (c) => {
                cut(c, [[0, -6 * sd], [190, -2 * sd], [196, 0], [10, 10 * sd]], '#c9cdd8', semente + 'lam' + sd, { border: 2, inner: (cc) => P.markerStroke(cc, [[20, 0], [170, 0]], '#eef1f6', 3, semente + 'brilho' + sd, 0.8) });
            });
            spr(g, 'tes-cabo' + sd, { x: -130, y: -70, w: 140, h: 140 }, (c) => {
                cut(c, P.ellipse(-62, sd * 26, 44, 28, 40), '#f2643c', semente + 'cabo' + sd, { border: 2.4 });
                c.fillStyle = '#2a1826';
                P.cutout(c, P.ellipse(-62, sd * 26, 26, 14, 40), '#3a2146', semente + 'furo' + sd, { border: 0, shadow: 0, tex: false });
            });
            g.restore();
        }
        spr(g, 'tes-pino', { x: -14, y: -14, w: 28, h: 28 }, (c) => cut(c, P.ellipse(0, 0, 8, 8, 20), '#7d8190', 'tes-pino', { border: 1.6 }));
    }
    ob('tesoura', (g, t, o) => {
        let abre = o.abre ?? 0.7;
        for (const tc of o.cortes ?? []) {
            const u = E.seg(t, tc - 0.25, tc + 0.12);
            if (u > 0 && u < 1) abre = Math.abs(Math.cos(u * Math.PI)) * 0.8;
        }
        tesoura(g, abre);
    });

    // lupa: aro escuro, vidro claro translúcido, cabo de madeira
    function lupa(g) {
        spr(g, 'lupa', { x: -90, y: -90, w: 260, h: 260 }, (c) => {
            cut(c, P.noodle([[48, 48], [150, 150]], 26, 22), '#a8743f', 'lupa-cabo', { inner: (cc, box) => D.woodGrain(cc, box, '#a8743f', { seed: 'lupa-veio' }) });
            cut(c, P.ellipse(0, 0, 70, 70, 64), '#2f3a44', 'lupa-aro', { border: 2.6 });
        });
        g.save();
        g.globalAlpha = 0.35;
        g.fillStyle = '#cdeef6';
        g.beginPath();
        g.arc(0, 0, 56, 0, Math.PI * 2);
        g.fill();
        g.restore();
        P.markerStroke(g, [[-30, -28], [-12, -42]], '#ffffff', 6, 'lupa-brilho', 0.7);
    }
    ob('lupa', (g, t, o) => lupa(g));

    // fones de ouvido soltos
    ob('fones', (g, t, o) => {
        spr(g, 'fones-soltos', { x: -110, y: -110, w: 220, h: 200 }, (c) => {
            cut(c, P.noodle(P.bezier([-70, 30], [-80, -90], [80, -90], [70, 30], 24), 18), '#3c6f74', 'fs-arco');
            for (const sd of [-1, 1]) cut(c, P.roundRect(sd * 70 - 22, 0, 44, 70, 18), '#2d4f55', 'fs-concha' + sd);
        });
    });

    // ondas de som: arcos de papel que viajam para +x ao longo de o.L
    ob('ondas', (g, t, o) => {
        const L = o.L ?? 400, n = 3;
        for (let i = 0; i < n; i++) {
            const f = ((t * (o.vel ?? 0.9) + i / n) % 1);
            const x = f * L, a = Math.sin(f * Math.PI);
            g.save();
            g.globalAlpha = a;
            g.translate(x, 0);
            spr(g, 'onda' + (o.cor ?? ''), { x: -20, y: -80, w: 60, h: 160 }, (c) => cut(c, P.noodle(P.bezier([0, -60], [30, -30], [30, 30], [0, 60], 16), 12), o.cor ?? '#ffd23f', 'onda', { border: 2 }));
            g.restore();
        }
    });

    // estrela dourada (carimbo visto de cima)
    ob('estrela', (g, t, o) => {
        g.rotate(Math.sin(t * 2) * 0.04);
        spr(g, 'estrela', { x: -110, y: -110, w: 220, h: 220 }, (c) => {
            const pts = [];
            for (let i = 0; i < 10; i++) {
                const r = i % 2 ? 40 : 92, a = -Math.PI / 2 + (i * Math.PI) / 5;
                pts.push([Math.cos(a) * r, Math.sin(a) * r]);
            }
            cut(c, pts, '#ffc93c', 'estrela', { border: 3.2 });
            cut(c, pts.map(([x, y]) => [x * 0.55, y * 0.55]), '#ffe07a', 'estrela-dentro', { border: 0, shadow: 0 });
        });
    });

    // mini criador (para telas de celular e cartões de take): o mesmo personagem, menor
    function miniCriador(g, t, ctx, o = {}) {
        const k = { de: { pose: o.pose ?? 'explica', rosto: o.rosto ?? 'feliz' }, para: { pose: o.pose ?? 'explica', rosto: o.rosto ?? 'feliz', t: 0 }, u: 1 };
        Personagens.criador(g, t, { k, fala: o.fala ?? 0, chave: o.chave ?? 'criador' }, ctx);
    }

    // tela do celular: o vídeo já editado tocando, limpo (o criador falando, barra de progresso)
    ob('tela_video_limpo', (g, t, o, ctx) => {
        spr(g, 'tela-limpa-fundo', { x: -140, y: -280, w: 280, h: 560 }, (c) => {
            Cenarios.parede(c, -140, -280, 280, 560, '#4b2552', 'tela-parede');
            cut(c, rect(-140, 150, 280, 140), '#bf8a55', 'tela-mesa', { border: 0, shadow: 0 });
        });
        g.save();
        g.translate(0, 160);
        g.scale(0.5, 0.5);
        miniCriador(g, t, ctx, { rosto: 'feliz', pose: 'explica', fala: Palco.boca(t) });
        g.restore();
        // barra de progresso do vídeo
        const p = E.seg(t, o.entra ?? 0, (o.entra ?? 0) + 6);
        g.fillStyle = 'rgba(251,247,238,0.5)';
        g.fillRect(-110, 240, 220, 6);
        g.fillStyle = '#ff4b3e';
        g.fillRect(-110, 240, 220 * (0.2 + 0.7 * p), 6);
        g.beginPath();
        g.arc(-110 + 220 * (0.2 + 0.7 * p), 243, 9, 0, 7);
        g.fill();
    });

    // cartão de take: quadro de filme com o criador pequeno dizendo uma frase (rabisco, sem texto)
    ob('take', (g, t, o, ctx) => {
        const amassa = o.amassa != null ? E.seg(t, o.amassa, o.amassa + 0.5) : 0;
        if (amassa >= 1) return desenharBola(g, 0, 0, 1.4, 'take-bola' + o.rotulo);
        g.save();
        g.scale(1 - amassa * 0.5, 1 - amassa * 0.6);
        g.rotate(amassa * 0.5);
        spr(g, 'take:' + o.rotulo, { x: -170, y: -150, w: 340, h: 300 }, (c) => {
            cut(c, P.roundRect(-150, -130, 300, 260, 10), '#2f2b36', 'take' + o.rotulo, { shadow: 0.3 });
            c.fillStyle = '#14121a';
            for (let x = -140; x < 150; x += 26) (c.fillRect(x, -124, 14, 12), c.fillRect(x, 112, 14, 12));
            Cenarios.parede(c, -134, -104, 268, 206, '#4b2552', 'take-parede' + o.rotulo);
        });
        g.save();
        g.beginPath();
        g.rect(-134, -104, 268, 206);
        g.clip();
        g.translate(-40, 150);
        g.scale(0.42, 0.42);
        miniCriador(g, t, ctx, { rosto: o.rosto ?? 'neutro', pose: 'explica', fala: Palco.boca(t) * 0.6, chave: 'criador' });
        g.restore();
        g.save();
        g.translate(70, -50);
        g.scale(0.62, 0.62);
        spr(g, 'take-balao' + o.rotulo, { x: -110, y: -70, w: 220, h: 160 }, (c) => {
            cut(c, P.circleUnion([[0, 0, 50], [-40, 6, 40], [40, 6, 40]]), '#fbf7ee', 'tb' + o.rotulo, { border: 2.2 });
            cut(c, [[-30, 30], [-70, 70], [-6, 40]], '#fbf7ee', 'tbc' + o.rotulo, { border: 2 });
            P.scribble(c, -60, -10, 120, 2, 22, '#6d5a78', 'frase-igual', { scale: 1.2, alpha: 0.75 });
        });
        g.restore();
        Texto.etiqueta(g, o.rotulo, -86, -100, { tam: 30, rot: -0.05 });
        g.restore();
    });

    return { ficha, circulo, tesoura, lupa, desenharBola, miniCriador };
})();
