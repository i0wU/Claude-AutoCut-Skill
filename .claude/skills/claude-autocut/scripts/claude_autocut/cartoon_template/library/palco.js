// Palco (stage) of the Claude AutoCut cartoon mode: lê o storyboard e pinta, para cada segundo t, a cena
// certa no canvas de cima. É uma função pura de t: o HyperFrames manda o tempo (evento hf-seek) e o
// palco pinta aquele quadro, sempre igual. Motor de papel: motor/core.js, paper.js, kit.js, detail.js
// (drawn-by-code, MIT). Global: Palco.
//
// Registro (biblioteca e cenas do projeto):
//   Palco.cenario(nome, { fundo(g, t, p, ctx), frente(g, t, p, ctx) })
//   Palco.ator(nome, (g, t, est, ctx) => {...})        est = estado da chave atual (pose, rosto, olhar...)
//   Palco.objeto(tipo, (g, t, o, ctx) => {...})        o = item do storyboard + o.u (0..1 da entrada) e o.local
//   Palco.roteiro(idDaCena, { antes(g, t, ctx), depois(g, t, ctx), tela(g, t, ctx) })
// ctx = { cena, env, kit, voz(t), palavra(i), u(t, a, b) }.
const Palco = (() => {
    const reg = { cenarios: {}, atores: {}, objetos: {}, roteiros: {} };
    const E = Ease;
    let env = null, kit = null, SB = null, cfg = null, canvas = null, g0 = null, cenas = [], ultimo = 0, pronto = false, eventos = [];

    const cenario = (n, f) => (reg.cenarios[n] = f);
    const ator = (n, f) => (reg.atores[n] = f);
    const objeto = (n, f) => (reg.objetos[n] = f);
    const roteiro = (id, f) => (reg.roteiros[id] = f);

    // --- som e fala -------------------------------------------------------------------------
    // energia da voz no tempo t (0..1), do envelope medido na fonte (preparar.py)
    function voz(t) {
        const V = window.ENVELOPE;
        if (!V) return 0;
        const i = t * V.fps, a = Math.floor(i), f = i - a;
        return (V.v[a] ?? 0) * (1 - f) + (V.v[a + 1] ?? 0) * f;
    }
    // abertura da boca: a voz suavizada, com um piso para não tremer no silêncio
    function boca(t) {
        const v = (voz(t) * 0.5 + voz(t - 1 / 30) * 0.3 + voz(t + 1 / 30) * 0.2);
        return v < 0.12 ? 0 : Math.min(1, (v - 0.12) / 0.6);
    }
    const palavra = (i) => (window.PALAVRAS ?? [])[i];

    // tempo da FONTE → tempo do vídeo de baixo. Sem mapa (fonte inteira) é a identidade. Com base editada,
    // o storyboard da variante traz "mapa" (trechos mantidos: src_start/src_end → out_start/out_end) e o
    // tempo que caía num corte vai para o começo do trecho seguinte. Roteiros com tempos fixos usam isto.
    function T(t) {
        const mapa = SB && SB.mapa;
        if (!mapa || !mapa.length) return t;
        for (const s of mapa) {
            if (t < s.src_start) return s.out_start;
            if (t <= s.src_end) return s.out_start + (t - s.src_start);
        }
        return mapa[mapa.length - 1].out_end;
    }

    // piscada determinística: 0 aberto, 1 fechado
    function piscar(t, semente) {
        const r = Motion.rng('pisca' + semente);
        const per = 2.8 + r() * 1.9, off = r() * per;
        const x = (((t + off) % per) + per) % per;
        return x < 0.14 ? Math.sin((x / 0.14) * Math.PI) : 0;
    }

    // --- chaves -----------------------------------------------------------------------------
    // chaves: [{ t, ...campos }] em tempo absoluto. Devolve { de, para, u }: a chave anterior, a atual e
    // o quanto da transição entre elas já correu (dur s, inOut). Antes da primeira, fica na primeira.
    // cada chave herda os campos das anteriores (fones postos continuam postos), menos t, dur e nega
    const acumuladas = new WeakMap();
    function acumular(chaves) {
        if (!acumuladas.has(chaves)) {
            let leva = {};
            acumuladas.set(chaves, chaves.map((k) => {
                const m = { ...leva, ...k };
                const { t: _t, dur: _d, nega: _n, ...resto } = m;
                leva = resto;
                return m;
            }));
        }
        return acumuladas.get(chaves);
    }
    function chaveEm(chaves0, t, dur = 0.38) {
        if (!chaves0 || !chaves0.length) return { de: {}, para: {}, u: 1 };
        const chaves = acumular(chaves0);
        let i = 0;
        while (i + 1 < chaves.length && chaves[i + 1].t <= t) i++;
        const para = chaves[i], de = i > 0 ? chaves[i - 1] : chaves[i];
        const d = para.dur ?? dur;
        return { de, para, u: t < para.t ? 1 : E.inOut(E.seg(t, para.t, para.t + d)) };
    }
    // mistura numérica de um campo entre duas chaves (número ou lista de números)
    function mistura(k, campo, padrao) {
        const a = k.de[campo] ?? k.para[campo] ?? padrao, b = k.para[campo] ?? a;
        if (Array.isArray(a)) return a.map((x, i) => E.lerp(x, b[i] ?? x, k.u));
        if (typeof a === 'number') return E.lerp(a, b, k.u);
        return k.u < 0.5 ? a : b;
    }

    // --- câmera -----------------------------------------------------------------------------
    // camera: [[t, cx, cy, zoom], ...] em tempo absoluto e coordenadas do cenário
    function camera(g, chaves, t) {
        if (!chaves || !chaves.length) return Motion.cam(g, env, env.W / 2, env.H / 2, 1);
        const fr = chaves.map(([tt, cx, cy, z, r]) => [tt, [cx, cy, z ?? 1, r ?? 0]]);
        const [cx, cy, z, r] = Motion.keys(fr, t);
        Motion.cam(g, env, cx, cy, z, r);
    }

    // --- cena -------------------------------------------------------------------------------
    function ctxDe(c) {
        return { cena: c, env, kit, voz, boca, palavra, piscar, u: (t, a, b) => E.seg(t, a, b), chaveEm, mistura };
    }

    function entrada(o, t) {
        // u: 0 antes de entrar, 1 em cena, de volta a 0 ao sair (para pop/sai)
        const a = o.entra ?? -1e9, b = o.sai ?? 1e9, de = o.dur_entrada ?? 0.35, ds = o.dur_saida ?? 0.3;
        if (t < a || t > b + ds) return null;
        return { ue: E.seg(t, a, a + de), us: E.seg(t, b, b + ds), local: t - a };
    }

    function aplicarEfeito(g, o, ent) {
        const ef = o.efeito ?? 'pop';
        const ue = ent.ue, us = ent.us;
        let a = 1 - us, s = 1, dx = 0, dy = 0, r = 0;
        if (ef === 'pop') {
            s = ue < 1 ? Math.max(0.001, E.back(ue)) : 1;
            s *= 1 - us * 0.6;
        } else if (ef === 'cai') {
            dy = -(1 - E.out(ue)) * 420;
            r = (1 - E.out(ue)) * 0.25;
        } else if (ef === 'sobe') {
            dy = (1 - E.out(ue)) * 260;
            a *= ue;
        } else if (ef === 'desliza_esq') {
            dx = -(1 - E.out(ue)) * 700;
        } else if (ef === 'desliza_dir') {
            dx = (1 - E.out(ue)) * 700;
        } else if (ef === 'aparece') {
            a *= ue;
        }
        if (o.flutua) dy += Math.sin(ent.local * 2.2 + (o.x ?? 0) * 0.013) * o.flutua;
        if (o.sai_efeito === 'cai' && us > 0) {
            dy += E.in(us) * 600;
            r += us * 0.6;
            a = 1;
        }
        return { a, s, dx, dy, r };
    }

    function desenharObjetos(g, c, t, camada, cx) {
        for (const o of c.objetos ?? []) {
            if ((o.camada ?? 'meio') !== camada) continue;
            const f = reg.objetos[o.tipo];
            if (!f) continue;
            const ent = entrada(o, t);
            if (!ent) continue;
            const ef = aplicarEfeito(g, o, ent);
            if (ef.a <= 0.001) continue;
            g.save();
            g.globalAlpha *= ef.a;
            g.translate((o.x ?? 0) + ef.dx, (o.y ?? 0) + ef.dy);
            g.rotate((o.rot ?? 0) + ef.r);
            const s = (o.s ?? 1) * ef.s;
            g.scale(s, s);
            f(g, t, { ...o, u: ent.ue, us: ent.us, local: ent.local }, cx);
            g.restore();
        }
    }

    // ator com `partes: true` (o criador atrás da mesa) é pintado em duas vezes: o corpo antes da mesa,
    // os braços depois dela, para as mãos ficarem em cima do tampo
    function desenharAtores(g, c, t, camada, cx) {
        for (const a0 of c.atores ?? []) {
            let a = a0;
            if (a0.partes && camada === 'bracos') a = { ...a0, parte: 'bracos' };
            else if (a0.partes && (a0.camada ?? 'meio') === camada) a = { ...a0, parte: 'corpo' };
            else if ((a0.camada ?? 'meio') !== camada) continue;
            const f = reg.atores[a.nome];
            if (!f) continue;
            const k = chaveEm(a.chaves, t);
            const pos = mistura(k, 'pos', [a.x ?? 0, a.y ?? 0]);
            const s = mistura(k, 's', a.s ?? 1);
            g.save();
            g.translate(pos[0], pos[1]);
            g.scale(s, s);
            f(g, t, { ...a, k, fala: a.fala ? boca(t) : 0 }, cx);
            g.restore();
        }
    }

    // --- espera (idle motion) -----------------------------------------------------------------------
    // Pausa sem fala e sem evento marcado congelaria o topo. Fora dos eventos
    // (chaves, entradas, saídas, cortes, textos, câmera, troca de cena) e das palavras, o peso da espera sobe devagar
    // depois de ESPERA_S e volta a zero antes do próximo evento. Objeto que já se mexe sozinho dispensa a espera.
    const ESPERA_S = 0.4, ANIMADOS = new Set(['ondas', 'interrogacao', 'estrela']);
    function montarEventos() {
        const ev = [];
        for (const c of cenas) {
            ev.push(c.t0, c.t1);
            for (const k of c.camera ?? []) ev.push(k[0]);
            for (const a of c.atores ?? []) for (const k of a.chaves ?? []) ev.push(k.t);
            for (const o of c.objetos ?? []) for (const x of [o.entra, o.sai, o.amassa, o.risca, ...(o.cortes ?? [])]) ev.push(x);
            for (const x of c.textos ?? []) ev.push(x.t, x.ate);
        }
        for (const w of window.PALAVRAS ?? []) ev.push(w.s, w.e);
        return ev.filter((x) => Number.isFinite(x)).sort((a, b) => a - b);
    }
    function espera(t, c) {
        if ((c.objetos ?? []).some((o) => (ANIMADOS.has(o.tipo) || o.flutua) && t >= (o.entra ?? -1e9) && t <= (o.sai ?? 1e9))) return 0;
        let lo = 0, hi = eventos.length;
        while (lo < hi) {
            const m = (lo + hi) >> 1;
            if (eventos[m] < t) lo = m + 1;
            else hi = m;
        }
        // entra ESPERA_S depois do último evento; volta ao lugar até o próximo, chegando nele exatamente (sem parar antes)
        const entra = E.seg(t - (eventos[lo - 1] ?? -1e9), ESPERA_S, ESPERA_S + 0.8), sai = E.seg((eventos[lo] ?? 1e9) - t, 0, 0.7);
        return E.inOut(Math.min(entra, sai));
    }

    function desenharCena(g, c, t) {
        const cx = ctxDe(c);
        const cen = reg.cenarios[c.cenario?.nome ?? c.cenario];
        const p = typeof c.cenario === 'object' ? c.cenario : {};
        const rot = reg.roteiros[c.roteiro ?? c.id] ?? {};
        g.save();
        camera(g, c.camera, t);
        const h = espera(t, c);
        if (h > 0) {   // espera: a câmera respira (até 3% e leve deriva), sem ação nova; entra e sai suave
            const z = 1 + h * 0.03 * (0.5 - 0.5 * Math.cos(t * 0.7)), dx = h * 12 * Math.sin(t * 0.37);
            g.translate(env.W / 2 + dx, env.H / 2);
            g.scale(z, z);
            g.translate(-env.W / 2, -env.H / 2);
        }
        if (cen?.fundo) cen.fundo(g, t, p, cx);
        desenharObjetos(g, c, t, 'fundo', cx);
        if (rot.antes) rot.antes(g, t, cx);
        desenharAtores(g, c, t, 'meio', cx);
        desenharObjetos(g, c, t, 'meio', cx);
        if (cen?.frente) cen.frente(g, t, p, cx);
        desenharAtores(g, c, t, 'bracos', cx);
        desenharAtores(g, c, t, 'frente', cx);
        desenharObjetos(g, c, t, 'frente', cx);
        if (rot.depois) rot.depois(g, t, cx);
        g.restore();
        // na tela (sem câmera): textos grandes e o que o roteiro quiser por cima
        if (rot.tela) rot.tela(g, t, cx);
        for (const tx of c.textos ?? []) Texto.titulo(g, t, tx, env);
    }

    // --- transições -------------------------------------------------------------------------
    const bordas = new Map();
    function bordaRasgada(semente, n = 60) {
        if (!bordas.has(semente)) {
            const pts = [];
            for (let i = 0; i <= n; i++) {
                const y = -60 + (i / n) * (env.H + 120);
                pts.push([Motion.noise1(semente, i * 0.35) * 26 + Motion.noise1(semente + 'f', i * 2.3) * 7, y]);
            }
            bordas.set(semente, pts);
        }
        return bordas.get(semente);
    }

    function transicao(g, a, b, t, tr) {
        const u = E.inOut(E.seg(t, b.t0, b.t0 + (tr.dur ?? 0.6)));
        const A = Motion.layer(env, 'A', (c) => desenharCena(c, a, t));
        const B = Motion.layer(env, 'B', (c) => desenharCena(c, b, t));
        Motion.drawLayer(g, env, A);
        if (tr.tipo === 'zoom') {
            g.save();
            g.globalAlpha = u;
            Motion.drawLayer(g, env, B);
            g.restore();
            return;
        }
        // folha nova entra pela direita com a borda esquerda rasgada (papel branco + sombra)
        const x = E.lerp(env.W + 60, -60, u);
        const borda = bordaRasgada('tr' + b.id).map(([dx, y]) => [x + dx, y]);
        const poly = [...borda, [env.W + 400, env.H + 100], [env.W + 400, -100]];
        g.save();
        g.translate(10, 4);
        g.fillStyle = 'rgba(20,6,26,0.28)';
        Paper.tracePath(g, poly);
        g.fill();
        g.restore();
        g.save();
        g.fillStyle = '#f7f1e3';
        Paper.tracePath(g, borda.map(([px, py]) => [px - 9, py]).concat([[env.W + 400, env.H + 100], [env.W + 400, -100]]));
        g.fill();
        Paper.tracePath(g, poly);
        g.clip();
        Motion.drawLayer(g, env, B);
        g.restore();
    }

    let pintado = null;
    function desenhar(t) {
        ultimo = t;
        if (!pronto || t === pintado) return;
        pintado = t;
        const g = g0;
        g.setTransform(1, 0, 0, 1, 0, 0);
        g.globalAlpha = 1;
        g.globalCompositeOperation = 'source-over';
        g.clearRect(0, 0, canvas.width, canvas.height);
        g.fillStyle = cfg.fundo ?? '#2a1826';
        g.fillRect(0, 0, canvas.width, canvas.height);
        g.setTransform(env.k, 0, 0, env.k, 0, 0);
        let i = cenas.findIndex((c) => t >= c.t0 && t < c.t1);
        if (i < 0) i = t < cenas[0].t0 ? 0 : cenas.length - 1;
        const c = cenas[i], tr = c.transicao, ant = cenas[i - 1];
        g.save();
        if (ant && tr && tr.tipo !== 'corte' && t < c.t0 + (tr.dur ?? 0.6)) transicao(g, ant, c, t, tr);
        else desenharCena(g, c, t);
        g.restore();
        g.setTransform(1, 0, 0, 1, 0, 0);
        kit.grainPost(g, cfg.grao ?? 0.32);
    }

    // --- início -----------------------------------------------------------------------------
    async function carregarFontes(lista) {
        for (const f of lista) {
            const ff = new FontFace(f.family, `url(${f.src})`);
            await ff.load();
            document.fonts.add(ff);
        }
    }

    function iniciar(o) {
        cfg = o;
        SB = o.storyboard;
        cenas = SB.cenas.slice().sort((a, b) => a.t0 - b.t0);
        eventos = montarEventos();
        canvas = document.getElementById(o.canvas);
        g0 = canvas.getContext('2d');
        const W = o.logico[0], H = o.logico[1];
        const k = canvas.width / W;
        env = { W, H, k, fps: o.fps, duration: o.duracao, total: Math.round(o.duracao * o.fps), px: [canvas.width, canvas.height], state: {} };
        const pronta = (async () => {
            await carregarFontes(o.fontes ?? []);
            kit = PaperKit.make(env, { font: 'Hand' });
            env.state.kit = kit;
            // const no topo de um script clássico não vira window.Divisoria: conferir pelo nome
            if (typeof Divisoria !== 'undefined' && o.divisoria) Divisoria.desenhar(document.getElementById(o.divisoria.canvas), o.divisoria);
            pronto = true;
            desenhar(ultimo || (window.__hfThreeTime ?? 0) + (o.deslocamento ?? 0));
        })();
        window.__hf = window.__hf || {};
        window.__hf.buildReady = window.__hf.buildReady || {};
        window.__hf.buildReady['palco-podcast'] = pronta;
        // trecho: a composição começa em `deslocamento` segundos da fonte
        const desl = o.deslocamento ?? 0;
        window.addEventListener('hf-seek', (ev) => desenhar(ev.detail.time + desl));
        // reserva: o adaptador do Anime.js também procura objetos com seek/pause/play
        window.__hfAnime = window.__hfAnime || [];
        window.__hfAnime.push({ seek: (ms) => desenhar(ms / 1000 + desl), pause() {}, play() {} });
        window.Palco_desenhar = desenhar;
        return pronta;
    }

    return { iniciar, desenhar, cenario, ator, objeto, roteiro, voz, boca, piscar, chaveEm, mistura, reg, T, get env() { return env; }, get kit() { return kit; } };
})();
