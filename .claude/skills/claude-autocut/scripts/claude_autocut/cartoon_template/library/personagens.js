// Personagens do modo podcast-animado, em papel recortado (cada parte é uma peça de papel com borda
// branca, textura de marcador e sombra para baixo e para a direita). Originais do Claude AutoCut (MIT).
//
//   criador  apresentador de meio corpo atrás da mesa. Origem = beira da mesa, no meio do corpo.
//            chaves: { t, pose, rosto, olhar:[dx,dy], inclina, nega, ombro }  (ver POSES e ROSTOS)
//            cores: est.cores (pele, cabelo, barba, camiseta, armacao; com_barba, com_oculos, com_relogio).
//   ia       notebook com rosto na tela. Origem = frente da base, em cima da mesa.
//            chaves: { t, rosto, ligado (0..1), fones (0..1), olhar:[dx,dy] }
//   mao_celular  mão do espectador segurando um celular (plano fechado). Origem = centro do celular.
//            est.tela(g, t, ctx) pinta o que passa na tela (recortado no vidro).
const Personagens = (() => {
    const P = Paper, D = PaperDetail, E = Ease;
    const spr = (g, key, box, fn, res = 1.7) => Motion.sprite(key, box, Palco.env.k * res, fn).draw(g);
    const cut = (c, pts, col, seed, o = {}) => P.cutout(c, pts, col, seed, { border: 2.6, shadow: 0.16, ...o });

    // ---------------------------------------------------------------------------------- criador
    // Generic host by default (no beard, no glasses, no watch). Turn features on per storyboard actor with
    // "cores": {"com_barba": true, "com_oculos": true, "com_relogio": true} and change any color.
    const COR_CRIADOR = {
        pele: '#c98b6b', cabelo: '#5a3a26', barba: '#4a3328', camiseta: '#2f7d78', gola: '#3c8f89',
        armacao: '#3d3a4a', lente: '#cfe6f2', olho: '#2a1d1f', labio: '#9c4f45', boca: '#4a1f26',
        relogio: '#2b2830', pulseira: '#e0a43a', suor: '#9fd9f2',
        com_barba: false, com_oculos: false, com_relogio: false,
    };
    const OMBRO = 128, OMBRO_Y = -252;
    // [cotovelo, mão, pose da mão, giro extra] por braço: direito do personagem = esquerda da imagem
    const POSES = {
        mesa: { d: [[-184, -118], [-96, -44], 'rest', 0], e: [[184, -118], [96, -44], 'rest', 0] },
        maos_juntas: { d: [[-176, -104], [-34, -150], 'fist', 0.3], e: [[176, -104], [34, -150], 'fist', -0.3] },
        um: { d: [[-212, -150], [-190, -312], 'point', 0], e: [[184, -118], [96, -44], 'rest', 0] },
        aponta_si: { d: [[-206, -132], [-58, -196], 'pointBack', 0.15], e: [[184, -118], [96, -44], 'rest', 0] },
        ombros: { d: [[-196, -128], [-262, -212], 'palm', -0.9], e: [[196, -128], [262, -212], 'palm', 0.9], ombro: -14 },
        nao: { d: [[-206, -118], [-150, -272], 'palm', -0.15], e: [[206, -118], [150, -272], 'palm', 0.15], aceno: 1 },
        aponta_dir: { d: [[-184, -118], [-96, -44], 'rest', 0], e: [[222, -176], [330, -226], 'pointBack', 0] },
        apresenta: { d: [[-184, -118], [-96, -44], 'rest', 0], e: [[214, -150], [316, -186], 'open', 0.5] },
        coca_cabeca: { d: [[-214, -330], [-112, -488], 'open', 0.5], e: [[184, -118], [96, -44], 'rest', 0], cocar: 1 },
        explica: { d: [[-188, -118], [-96, -176], 'open', -0.35], e: [[188, -118], [96, -176], 'palm', 0.35], gesto: 1 },
        joinha: { d: [[-184, -118], [-96, -44], 'rest', 0], e: [[208, -150], [214, -292], 'fist', 0], },
    };
    const ROSTOS = {
        neutro: { sob: [0, 0], palp: 0.28, boca: 'sorriso', abre: 0 },
        feliz: { sob: [-4, 0.1], palp: 0.18, boca: 'sorrisao', abre: 0 },
        sem_graca: { sob: [-6, -0.32], palp: 0.22, boca: 'torto', abre: 0, suor: 1 },
        surpreso: { sob: [-13, 0.05], palp: 0.04, boca: 'o', abre: 0.6 },
        confiante: { sob: [-2, 0.18], palp: 0.36, boca: 'meio', abre: 0 },
        pensativo: { sob: [-8, -0.2], palp: 0.3, boca: 'reto', abre: 0 },
    };

    function braco(g, t, sh, el, hd, lado, pose, giro, cores, chave) {
        const pele = cores.pele, braco = D.shade(pele, -4);
        // braço e antebraço em sprites no sistema do próprio segmento: a textura anda junto com o braço
        const seg = (a, b, w0, w1, cor, nome) => {
            const L = Math.hypot(b[0] - a[0], b[1] - a[1]), ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
            const Lq = Math.round(L / 6) * 6;
            g.save();
            g.translate(a[0], a[1]);
            g.rotate(ang);
            spr(g, `${chave}:${nome}:${Lq}`, { x: -w0, y: -w0, w: Lq + 2 * w0, h: 2 * w0 }, (c) => cut(c, P.noodle([[0, 0], [Lq, 0]], w0, w1), cor, `${chave}${nome}`, { tex: { alpha: [0.14, 0.28] } }));
            g.restore();
        };
        seg(sh, el, 44, 40, braco, 'braco' + lado);
        seg(el, hd, 40, 34, braco, 'ante' + lado);
        // manga curta da camiseta por cima do ombro
        const ang = Math.atan2(el[1] - sh[1], el[0] - sh[0]);
        g.save();
        g.translate(sh[0], sh[1]);
        g.rotate(ang);
        spr(g, `${chave}:manga${lado}`, { x: -50, y: -50, w: 160, h: 100 }, (c) => {
            cut(c, D.spline([[-18, -30], [36, -33], [74, -28], [78, 0], [73, 28], [30, 32], [-22, 28]], 6), cores.camiseta, chave + 'manga' + lado, { tex: { alpha: [0.18, 0.34] } });
            P.markerStroke(c, [[70, -26], [74, 0], [70, 26]], D.shade(cores.camiseta, 9), 4, chave + 'bainha' + lado, 0.7);
        });
        g.restore();
        // pulso: relógio no esquerdo (direita da imagem), pulseira vermelha no direito
        const rot = Math.atan2(hd[1] - el[1], hd[0] - el[0]);
        const pw = [E.lerp(el[0], hd[0], 0.82), E.lerp(el[1], hd[1], 0.82)];
        g.save();
        g.translate(pw[0], pw[1]);
        g.rotate(rot);
        if (lado === 'e' && cores.com_relogio) {
            spr(g, `${chave}:relogio`, { x: -16, y: -26, w: 32, h: 52 }, (c) => {
                cut(c, P.roundRect(-8, -22, 16, 44, 4), cores.relogio, chave + 'pulseira-rel', { border: 1.6 });
                cut(c, P.roundRect(-11, -13, 22, 26, 6), D.shade(cores.relogio, 6), chave + 'mostrador', { border: 1.6, inner: (cc) => { cc.fillStyle = '#7fd6c2'; cc.fillRect(-6, -8, 12, 16); } });
            });
        } else {
            spr(g, `${chave}:pulseira`, { x: -10, y: -24, w: 20, h: 48 }, (c) => cut(c, P.roundRect(-4, -20, 8, 40, 4), cores.pulseira, chave + 'pulseira', { border: 1.4 }));
        }
        g.restore();
        const r = rot + Math.PI / 2 + (giro ?? 0);
        D.hand(g, hd[0], hd[1], 58, r, pose, { skin: pele, side: lado === 'd' ? 'right' : 'left' });
    }

    function tronco(g, cores, chave, ombro) {
        spr(g, `${chave}:pescoco`, { x: -40, y: -350, w: 80, h: 100 }, (c) => cut(c, P.roundRect(-27, -342, 54, 86, 18), D.shade(cores.pele, -7), chave + 'pescoco', { border: 0, shadow: 0, tex: { alpha: [0.1, 0.2] } }));
        g.save();
        g.translate(0, ombro * 0.5);
        spr(g, `${chave}:tronco`, { x: -190, y: -310, w: 380, h: 330 }, (c) => {
            cut(c, D.spline([[-118, -266], [-52, -284], [52, -284], [118, -266], [150, -190], [160, 0], [-160, 0], [-150, -190]], 6), cores.camiseta, chave + 'tronco', { tex: { alpha: [0.18, 0.36], len: [30, 80] } });
            // dobras do algodão
            for (const [a, b, s] of [[[-96, -150], [-60, -120], 'd1'], [[70, -96], [110, -130], 'd2'], [[-40, -40], [10, -60], 'd3']]) P.markerStroke(c, [a, b], D.shade(cores.camiseta, -7), 4, chave + s, 0.5);
            // gola careca em ribana
            cut(c, P.noodle(P.bezier([-50, -282], [-30, -246], [30, -246], [50, -282], 14), 15), cores.gola, chave + 'gola', { border: 1.6, shadow: 0.12, inner: (cc, box) => D.rib(cc, box, cores.gola, { step: 7, width: 2.5, angle: Math.PI / 2 }) });
        }, 1.6);
        g.restore();
    }

    function cabeca(g, t, est, cores, chave) {
        const k = est.k, rosto = ROSTOS[k.para.rosto ?? 'neutro'] ?? ROSTOS.neutro, rostoAnt = ROSTOS[k.de.rosto ?? k.para.rosto ?? 'neutro'] ?? rosto;
        const u = k.u, mix = (a, b) => E.lerp(a, b, u);
        const olhar = Palco.mistura(k, 'olhar', [0, 0]);
        const pisca = Palco.piscar(t, chave);
        const fala = est.fala ?? 0;
        // cabeça viva: respira, acompanha a fala, nega se pedido
        const nega = (k.para.nega ? Math.sin((t - k.para.t) * 15) * 0.09 * (1 - E.seg(t, k.para.t + 0.9, k.para.t + 1.3)) : 0);
        const inc = Palco.mistura(k, 'inclina', 0) + Math.sin(t * 1.7) * 0.018 + fala * 0.03 * Math.sin(t * 9) + nega;
        g.save();
        g.translate(nega * 60, -428 + Math.sin(t * 2.1) * 2.2 - fala * 3);
        g.rotate(inc);
        // orelhas
        spr(g, `${chave}:orelhas`, { x: -112, y: -50, w: 224, h: 100 }, (c) => {
            for (const sd of [-1, 1]) cut(c, D.spline([[sd * 80, -24], [sd * 98, -30], [sd * 106, -2], [sd * 96, 26], [sd * 80, 22]], 5), D.shade(cores.pele, -3), chave + 'orelha' + sd, { border: 2, tex: { alpha: [0.1, 0.2] } });
        });
        // rosto
        spr(g, `${chave}:rosto`, { x: -100, y: -125, w: 200, h: 250 }, (c) => {
            cut(c, D.spline([[-78, -72], [-50, -106], [0, -114], [50, -106], [78, -72], [87, -10], [81, 40], [58, 86], [0, 104], [-58, 86], [-81, 40], [-87, -10]], 8), cores.pele, chave + 'rosto', { tex: { alpha: [0.1, 0.22] } });
        });
        // barba (opcional): do maxilar ao queixo, com bigode separado
        if (cores.com_barba) spr(g, `${chave}:barba`, { x: -100, y: -30, w: 200, h: 150 }, (c) => {
            cut(c, D.spline([[-88, -10], [-82, 40], [-60, 90], [0, 116], [60, 90], [82, 40], [88, -10], [74, 18], [56, 46], [26, 54], [0, 52], [-26, 54], [-56, 46], [-74, 18]], 8), cores.barba, chave + 'barba', { border: 2.2, tex: false, inner: (cc, box) => D.strands(cc, box, cores.barba, { seed: chave + 'barba', angle: Math.PI / 2 }) });
        }, 1.6);
        // nariz
        spr(g, `${chave}:nariz`, { x: -26, y: -20, w: 52, h: 70 }, (c) => {
            cut(c, D.spline([[-6, -12], [8, -14], [14, 20], [20, 32], [4, 40], [-14, 34], [-10, 18]], 5), D.shade(cores.pele, -6), chave + 'nariz', { border: 1.8, shadow: 0.2, tex: { alpha: [0.1, 0.2] } });
        });
        // olhos: branco, pupila, pálpebra pesada (um tom mais escuro que o rosto) que nunca sobe toda
        const palp = Math.max(mix(rostoAnt.palp, rosto.palp), pisca);
        for (const sd of [-1, 1]) {
            const ex = sd * 34, ey = -18;
            g.save();
            g.translate(ex, ey);
            spr(g, `${chave}:olho${sd}`, { x: -20, y: -18, w: 40, h: 36 }, (c) => cut(c, P.ellipse(0, 0, 15, 12.5, 32), '#fbf6ea', chave + 'olho' + sd, { border: 0, shadow: 0.12, jag: 0.4, tex: { alpha: [0.06, 0.12] } }), 2);
            g.save();
            g.beginPath();
            g.ellipse(0, 0, 15, 12.5, 0, 0, Math.PI * 2);
            g.clip();
            g.fillStyle = cores.olho;
            g.beginPath();
            g.ellipse(olhar[0] * 6, olhar[1] * 4 + 1, 7.5, 8.5, 0, 0, Math.PI * 2);
            g.fill();
            g.fillStyle = '#fff';
            g.beginPath();
            g.arc(olhar[0] * 6 + 2.6, olhar[1] * 4 - 2.4, 2.4, 0, Math.PI * 2);
            g.fill();
            // pálpebra
            g.fillStyle = D.shade(cores.pele, -12);
            g.fillRect(-18, -16, 36, 4 + palp * 28);
            if (palp > 0.9) {
                g.strokeStyle = cores.olho;
                g.lineWidth = 2.6;
                g.beginPath();
                g.arc(0, -2, 13, Math.PI * 0.15, Math.PI * 0.85);
                g.stroke();
            }
            g.restore();
            g.restore();
        }
        // sobrancelhas grossas: sobem, descem e inclinam com o humor
        const sob = [mix(rostoAnt.sob[0], rosto.sob[0]), mix(rostoAnt.sob[1], rosto.sob[1])];
        for (const sd of [-1, 1]) {
            const x0 = sd * 16, x1 = sd * 54, yb = -50 + sob[0] - fala * 2;
            const incl = sob[1] * sd;
            P.markerStroke(g, [[x0, yb + incl * 22], [(x0 + x1) / 2, yb - 5], [x1, yb - incl * 6 + 3]], cores.cabelo, 9, chave + 'sob' + sd, 0.95);
        }
        // óculos (opcional), retangulares arredondados, por cima dos olhos
        if (cores.com_oculos) {
        g.save();
        g.lineJoin = 'round';
        for (const sd of [-1, 1]) {
            g.strokeStyle = D.shade(cores.armacao, -10);
            g.lineWidth = 7.5;
            g.beginPath();
            g.roundRect(sd * 34 - 29, -42, 58, 46, 15);
            g.stroke();
            g.strokeStyle = cores.armacao;
            g.lineWidth = 4.5;
            g.stroke();
            // brilho da lente
            g.strokeStyle = 'rgba(255,255,255,0.45)';
            g.lineWidth = 3;
            g.beginPath();
            g.moveTo(sd * 34 + 8, -36);
            g.lineTo(sd * 34 + 20, -24);
            g.stroke();
        }
        g.strokeStyle = cores.armacao;
        g.lineWidth = 5;
        g.beginPath();
        g.moveTo(-6, -24);
        g.quadraticCurveTo(0, -30, 6, -24);
        g.moveTo(-63, -30);
        g.lineTo(-84, -26);
        g.moveTo(63, -30);
        g.lineTo(84, -26);
        g.stroke();
        g.restore();
        }
        // bigode (com a barba)
        if (cores.com_barba) spr(g, `${chave}:bigode`, { x: -50, y: 18, w: 100, h: 40 }, (c) => {
            cut(c, D.spline([[-36, 36], [-18, 26], [0, 29], [18, 26], [36, 36], [18, 38], [0, 36], [-18, 38]], 5), D.shade(cores.barba, 4), chave + 'bigode', { border: 1.6, tex: false, inner: (cc, box) => D.strands(cc, box, cores.barba, { seed: chave + 'bigode', angle: 0.1 }) });
        });
        // boca: formato do humor + abertura pela voz de verdade
        const tipo = u < 0.5 ? rostoAnt.boca : rosto.boca;
        const abre = Math.max(mix(rostoAnt.abre, rosto.abre), fala);
        const by = 52;
        if (abre > 0.08) {
            const w = tipo === 'o' ? 12 : 17 + abre * 4, h = 4 + abre * 15;
            g.fillStyle = cores.boca;
            g.beginPath();
            g.moveTo(-w, by - 2);
            g.quadraticCurveTo(0, by - 4 - (tipo === 'sorrisao' ? -2 : 0), w, by - 2);
            g.quadraticCurveTo(w * 0.8, by + h, 0, by + h + 2);
            g.quadraticCurveTo(-w * 0.8, by + h, -w, by - 2);
            g.fill();
            g.fillStyle = '#f4ecda';
            g.fillRect(-w * 0.6, by - 2, w * 1.2, Math.min(4, h * 0.3));
            g.strokeStyle = cores.labio;
            g.lineWidth = 2.5;
            g.stroke();
        } else if (tipo === 'sorrisao') {
            g.fillStyle = cores.boca;
            g.beginPath();
            g.moveTo(-22, by - 3);
            g.quadraticCurveTo(0, by + 2, 22, by - 3);
            g.quadraticCurveTo(10, by + 18, 0, by + 18);
            g.quadraticCurveTo(-10, by + 18, -22, by - 3);
            g.fill();
            g.fillStyle = '#f4ecda';
            g.fillRect(-14, by - 1, 28, 4);
        } else {
            const pts = tipo === 'torto' ? [[-16, by + 4], [-6, by], [4, by + 4], [16, by - 2]]
                : tipo === 'reto' ? [[-14, by + 2], [14, by + 1]]
                : tipo === 'meio' ? [[-14, by + 2], [2, by + 5], [18, by - 3]]
                : tipo === 'o' ? null : [[-18, by - 1], [0, by + 7], [18, by - 1]];
            if (pts) P.markerStroke(g, pts, cores.boca, 5, chave + 'boca' + tipo, 0.95);
            else {
                g.fillStyle = cores.boca;
                g.beginPath();
                g.ellipse(0, by + 4, 8, 10, 0, 0, Math.PI * 2);
                g.fill();
            }
        }
        // cabelo por cima de tudo: topete com fios, laterais curtas mais escuras
        spr(g, `${chave}:cabelo`, { x: -110, y: -185, w: 220, h: 150 }, (c) => {
            for (const sd of [-1, 1]) cut(c, D.spline([[sd * 92, -40], [sd * 90, -92], [sd * 70, -120], [sd * 66, -76], [sd * 80, -36]], 5), D.shade(cores.cabelo, -4), chave + 'lateral' + sd, { border: 2, tex: false, inner: (cc, box) => D.strands(cc, box, cores.cabelo, { seed: chave + 'lat' + sd, angle: Math.PI / 2 }) });
            cut(c, D.spline([[-88, -64], [-92, -110], [-62, -148], [-14, -168], [44, -162], [86, -128], [94, -74], [74, -96], [44, -112], [4, -116], [-40, -110], [-70, -92]], 8), cores.cabelo, chave + 'topete', { border: 2.6, tex: false, inner: (cc, box) => D.strands(cc, box, cores.cabelo, { seed: chave + 'topete', angle: 0.35 }) });
            P.markerStroke(c, [[-50, -142], [-6, -156], [40, -150]], D.shade(cores.cabelo, 14), 4, chave + 'brilho', 0.55);
        }, 1.6);
        // gota de suor (sem graça)
        const suor = mix(rostoAnt.suor ?? 0, rosto.suor ?? 0);
        if (suor > 0.05) {
            const dy = ((t * 30) % 40) * 0.6;
            g.save();
            g.globalAlpha = suor;
            g.translate(96, -70 + dy);
            spr(g, `${chave}:suor`, { x: -16, y: -26, w: 32, h: 46 }, (c) => cut(c, [[0, -22], [9, -4], [10, 6], [0, 14], [-10, 6], [-9, -4]], cores.suor, chave + 'suor', { border: 2, shadow: 0.15 }));
            g.restore();
        }
        g.restore();
    }

    function criador(g, t, est, ctx) {
        const cores = { ...COR_CRIADOR, ...(est.cores ?? {}) }, chave = est.chave ?? 'criador';
        const k = est.k;
        const pa = POSES[k.de.pose ?? k.para.pose ?? 'mesa'] ?? POSES.mesa, pb = POSES[k.para.pose ?? 'mesa'] ?? POSES.mesa;
        const u = k.u;
        const ombro = E.lerp(pa.ombro ?? 0, pb.ombro ?? 0, u);
        g.save();
        g.translate(0, Math.sin(t * 2.1) * 1.4);
        if (est.parte !== 'bracos') {
            tronco(g, cores, chave, ombro);
            cabeca(g, t, est, cores, chave);
        }
        if (est.parte === 'corpo') {
            g.restore();
            return;
        }
        for (const lado of ['d', 'e']) {
            const A = pa[lado], B = pb[lado];
            const sx = (lado === 'd' ? -OMBRO : OMBRO), sh = [sx, OMBRO_Y + ombro];
            let el = [E.lerp(A[0][0], B[0][0], u), E.lerp(A[0][1], B[0][1], u) + ombro];
            let hd = [E.lerp(A[1][0], B[1][0], u), E.lerp(A[1][1], B[1][1], u) + ombro];
            // gestos vivos: aceno do "não", coçar a cabeça, mão que acompanha a fala
            const desde = t - (k.para.t ?? 0);
            if (pb.aceno) hd[0] += Math.sin(desde * 13) * 14 * u;
            if (pb.cocar && lado === 'd') (hd[0] += Math.sin(desde * 18) * 6 * u, hd[1] += Math.cos(desde * 18) * 4 * u);
            if (pb.gesto) hd[1] += Math.sin(t * 5.5 + (lado === 'd' ? 0 : 1.7)) * 10 * (0.4 + (est.fala ?? 0));
            const poseMao = u < 0.5 ? A[2] : B[2];
            const giro = E.lerp(A[3] ?? 0, B[3] ?? 0, u);
            braco(g, t, sh, el, hd, lado, poseMao, giro, cores, chave);
        }
        g.restore();
    }

    // ---------------------------------------------------------------------------------- ia
    const COR_IA = { casca: '#bfbccb', cascaEsc: '#9a97a8', moldura: '#34303f', telaOff: '#2b3442', tela: '#8fe3cf', rosto: '#21303a', fones: '#3c6f74', fonesAlmofada: '#2d4f55', tecla: '#8d8a9b' };
    const ROSTOS_IA = {
        feliz: { olho: 'aberto', boca: 'sorriso' }, atenta: { olho: 'grande', boca: 'o' }, ouvindo: { olho: 'fechado', boca: 'sorriso' },
        foco: { olho: 'estreito', boca: 'reto' }, orgulho: { olho: 'feliz', boca: 'sorrisao' }, dormindo: { olho: 'fechado', boca: 'reto' },
    };

    function ia(g, t, est, ctx) {
        const C = { ...COR_IA, ...(est.cores ?? {}) }, chave = est.chave ?? 'ia', k = est.k;
        const ligado = Palco.mistura(k, 'ligado', 1), fones = Palco.mistura(k, 'fones', 0);
        const olhar = Palco.mistura(k, 'olhar', [0, 0]);
        const r = ROSTOS_IA[k.para.rosto ?? 'feliz'] ?? ROSTOS_IA.feliz;
        const bob = (k.para.rosto === 'ouvindo' ? Math.sin(t * 6) * 3 : Math.sin(t * 2.4) * 1.2);
        // base em perspectiva, com teclado impresso e touchpad
        spr(g, `${chave}:base`, { x: -175, y: -60, w: 350, h: 90 }, (c) => {
            cut(c, [[-150, -34], [150, -34], [168, 4], [-168, 4]], C.casca, chave + 'base', { inner: (cc) => {
                cc.fillStyle = C.tecla;
                for (let row = 0; row < 3; row++) for (let i = 0; i < 13; i++) {
                    const y = -28 + row * 8, x0 = -126 - row * 4 + i * (20 + row * 0.6);
                    cc.globalAlpha = 0.85;
                    cc.fillRect(x0, y, 16, 5);
                }
                cc.globalAlpha = 1;
                cc.fillStyle = D.shade(C.casca, -6);
                cc.fillRect(-34, -5, 68, 8);
            } });
            cut(c, [[-168, 4], [168, 4], [164, 14], [-164, 14]], C.cascaEsc, chave + 'borda', { border: 1.6, shadow: 0.2 });
        }, 1.6);
        // tampa com moldura e tela
        g.save();
        g.translate(0, bob * 0.3);
        spr(g, `${chave}:tampa`, { x: -160, y: -270, w: 320, h: 250 }, (c) => {
            cut(c, P.roundRect(-140, -258, 280, 226, 16), C.moldura, chave + 'tampa', { shadow: 0.2 });
            c.fillStyle = '#52505e';
            c.beginPath();
            c.arc(0, -249, 3, 0, Math.PI * 2);
            c.fill();
        }, 1.6);
        // tela: apagada por baixo; a ligada entra de dentro para fora, como um tubo de TV
        const tx = -124, ty = -242, tw = 248, th = 196;
        g.save();
        g.beginPath();
        g.roundRect(tx, ty, tw, th, 8);
        g.clip();
        g.fillStyle = C.telaOff;
        g.fillRect(tx, ty, tw, th);
        if (ligado > 0.01) {
            const h = th * Math.min(1, ligado * 1.4), w = tw * Math.min(1, 0.15 + ligado);
            g.beginPath();
            g.rect(-w / 2, ty + th / 2 - h / 2, w, h);
            g.clip();
            spr(g, `${chave}:telaon`, { x: tx - 4, y: ty - 4, w: tw + 8, h: th + 8 }, (c) => cut(c, P.roundRect(tx, ty, tw, th, 8), C.tela, chave + 'tela', { border: 0, shadow: 0, tex: { alpha: [0.12, 0.28], len: [40, 120], h: [3, 6] } }), 1.6);
        }
        g.restore();
        // rosto na tela
        if (ligado > 0.2) {
            const a = E.seg(ligado, 0.2, 0.6);
            const pisca = Palco.piscar(t, chave);
            g.save();
            g.globalAlpha = a;
            g.translate(0, -150);
            const tipo = r.olho;
            for (const sd of [-1, 1]) {
                const ex = sd * 44 + olhar[0] * 8, ey = olhar[1] * 6;
                g.fillStyle = C.rosto;
                if (tipo === 'fechado' || pisca > 0.85) {
                    P.markerStroke(g, [[ex - 16, ey + 2], [ex, ey + 10], [ex + 16, ey + 2]], C.rosto, 6, chave + 'fech' + sd, 1);
                } else if (tipo === 'feliz') {
                    P.markerStroke(g, [[ex - 16, ey + 8], [ex, ey - 6], [ex + 16, ey + 8]], C.rosto, 6, chave + 'fel' + sd, 1);
                } else {
                    const hh = (tipo === 'grande' ? 26 : tipo === 'estreito' ? 9 : 20) * (1 - pisca * 0.9);
                    const ww = tipo === 'grande' ? 17 : 14;
                    g.beginPath();
                    g.roundRect(ex - ww, ey - hh, ww * 2, hh * 2, Math.min(ww, hh));
                    g.fill();
                    g.fillStyle = '#e9fff8';
                    g.beginPath();
                    g.arc(ex + 5, ey - hh * 0.45, 3.4, 0, Math.PI * 2);
                    g.fill();
                    if (tipo === 'estreito') P.markerStroke(g, [[ex - 18, ey - 18 + sd * 2], [ex + 18, ey - 18 - sd * 2]], C.rosto, 4, chave + 'cenho' + sd, 0.9);
                }
            }
            const bb = r.boca, by = 42;
            if (bb === 'o') {
                g.fillStyle = C.rosto;
                g.beginPath();
                g.ellipse(0, by, 9, 11, 0, 0, Math.PI * 2);
                g.fill();
            } else if (bb === 'sorrisao') {
                g.fillStyle = C.rosto;
                g.beginPath();
                g.moveTo(-26, by - 6);
                g.quadraticCurveTo(0, by, 26, by - 6);
                g.quadraticCurveTo(14, by + 22, 0, by + 22);
                g.quadraticCurveTo(-14, by + 22, -26, by - 6);
                g.fill();
            } else {
                const pts = bb === 'reto' ? [[-14, by], [14, by]] : [[-22, by - 4], [0, by + 9], [22, by - 4]];
                P.markerStroke(g, pts, C.rosto, 6, chave + 'boca' + bb, 1);
            }
            g.restore();
        }
        // fones de ouvido: arco por cima da tampa e conchas nas laterais
        if (fones > 0.01) {
            const dy = (1 - E.out(fones)) * -160;
            g.save();
            g.globalAlpha = Math.min(1, fones * 2);
            g.translate(0, dy);
            spr(g, `${chave}:fones`, { x: -190, y: -340, w: 380, h: 250 }, (c) => {
                cut(c, P.noodle(P.bezier([-150, -150], [-160, -330], [160, -330], [150, -150], 30), 22), C.fones, chave + 'arco', { inner: (cc, box) => D.rib(cc, box, C.fones, { step: 12, width: 3, angle: 0 }) });
                for (const sd of [-1, 1]) {
                    cut(c, P.roundRect(sd * 150 - 26, -200, 52, 96, 22), C.fonesAlmofada, chave + 'almofada' + sd);
                    cut(c, P.roundRect(sd * 150 - 18 + sd * 10, -190, 36, 76, 16), C.fones, chave + 'concha' + sd, { border: 2 });
                }
            }, 1.4);
            g.restore();
        }
        g.restore();
    }

    // ---------------------------------------------------------------------------------- mão com celular
    function mao_celular(g, t, est, ctx) {
        const pele = est.pele ?? '#e7b896', chave = est.chave ?? 'maocel';
        const bal = Math.sin(t * 1.6) * 0.012, manga = est.manga ?? '#5a7fb8';
        g.save();
        g.rotate(bal);
        // antebraço que vem de baixo, à direita, e a palma por trás do celular
        spr(g, `${chave}:braco`, { x: -200, y: 40, w: 600, h: 700 }, (c) => {
            cut(c, P.noodle([[330, 700], [90, 300]], 150, 128), manga, chave + 'manga', { inner: (cc, box) => D.knit(cc, box, manga, { seed: chave + 'malha', size: 14, alpha: 0.16 }) });
            cut(c, P.noodle(P.bezier([110, 330], [70, 270], [40, 240], [10, 210], 8), 104, 110), D.shade(pele, -3), chave + 'pulso');
            cut(c, D.spline([[-130, 110], [40, 70], [130, 170], [80, 290], [-110, 290]], 6), pele, chave + 'palma');
            P.markerStroke(c, [[106, 352], [24, 420]], D.shade(manga, -10), 5, chave + 'punho', 0.6);
        }, 1.3);
        spr(g, `${chave}:corpo`, { x: -170, y: -320, w: 340, h: 640 }, (c) => {
            cut(c, P.roundRect(-150, -300, 300, 600, 40), '#2c2833', chave + 'corpo', { shadow: 0.28 });
            c.fillStyle = '#4a4655';
            c.fillRect(-36, -288, 72, 7);
        }, 1.4);
        g.save();
        g.beginPath();
        g.roundRect(-134, -272, 268, 548, 22);
        g.clip();
        if (typeof est.tela === 'string') Palco.reg.objetos[est.tela]?.(g, t, est.tela_p ?? {}, ctx);
        else if (est.tela) est.tela(g, t, ctx);
        g.restore();
        // dedos que dão a volta pela borda esquerda (só as pontas aparecem) e o polegar pela direita
        spr(g, `${chave}:dedos`, { x: -200, y: 0, w: 420, h: 360 }, (c) => {
            [[40, 52, -2], [92, 58, -4], [146, 56, -6], [196, 46, -8]].forEach(([y, L, sh], i) => {
                const pts = D.taper([[-150 - 22, y], [-150 + L * 0.45, y + 2], [-150 + L, y + 4]], [30, 31, 24], 6);
                cut(c, pts, D.shade(pele, sh), chave + 'dedo' + i, { border: 2.2, shadow: 0.2 });
                P.markerStroke(c, [[-150 + L * 0.3, y - 8], [-150 + L * 0.34, y + 8]], D.shade(pele, -16), 1.8, chave + 'dobra' + i, 0.45);
                cut(c, P.roundRect(-150 + L - 15, y - 7 + 3, 12, 13, 5), D.shade(pele, 6), chave + 'unha' + i, { border: 0, shadow: 0, tex: false });
            });
            const pol = D.taper([[196, 300], [168, 214], [138, 150], [126, 112]], [44, 40, 34, 30], 6);
            cut(c, pol, D.shade(pele, 2), chave + 'polegar', { border: 2.4, shadow: 0.22 });
            cut(c, P.roundRect(120, 112, 18, 20, 7), D.shade(pele, 7), chave + 'unha-pol', { border: 0, shadow: 0, tex: false });
        }, 1.5);
        g.restore();
    }

    Palco.ator('criador', criador);
    Palco.ator('ia', ia);
    Palco.ator('mao_celular', mao_celular);
    return { COR_CRIADOR, COR_IA, POSES, ROSTOS, ROSTOS_IA, criador, ia, mao_celular };
})();
