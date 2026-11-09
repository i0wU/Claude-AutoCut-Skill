// Textos grandes do modo podcast-animado: palavra-chave, pergunta, número, frase curta. Anton em caixa
// alta, contorno escuro (tinta, nunca preto puro), sombra curta de papel colado, entrada com salto no
// tempo da palavra. Branco por padrão; as palavras de `destaque` saem em amarelo. Global: Texto.
//
// item: { t, ate, txt, destaque: ['NÃO'], cor: 'branco'|'amarelo', x, y, tam, giro, tempos: [t por palavra] }
//   txt com '|' quebra a linha de propósito. Sem `tempos`, a frase entra inteira em t.
//   x, y em coordenadas lógicas do canvas de cima (centro da primeira linha).
const Texto = (() => {
    const E = Ease;
    const COR = { branco: '#fbf7ee', amarelo: '#ffd23f', tinta: '#2a1826', vermelho: '#ff6b4a', menta: '#7fe0c4' };

    function palavrasDe(item) {
        const linhas = String(item.txt).toUpperCase().split('|').map((l) => l.trim().split(/\s+/));
        const dest = new Set((item.destaque ?? []).map((d) => d.toUpperCase().replace(/[.,!?;:]/g, '')));
        let n = 0;
        return linhas.map((ws) => ws.map((w) => ({ w, dest: dest.has(w.replace(/[.,!?;:]/g, '')), i: n++ })));
    }

    function titulo(g, t, item, env) {
        const t0 = item.t, t1 = item.ate ?? 1e9;
        if (t < t0 || t > t1 + 0.22) return;
        const tam = item.tam ?? 92, x = item.x ?? env.W / 2, y = item.y ?? 300;
        const sai = E.seg(t, t1, t1 + 0.22);
        const linhas = palavrasDe(item);
        g.save();
        g.font = `${tam}px "Anton"`;
        g.textBaseline = 'alphabetic';
        g.lineJoin = 'round';
        g.miterLimit = 2;
        const esp = tam * 0.24, alt = tam * 1.06;
        linhas.forEach((ws, li) => {
            const larg = ws.map((p) => g.measureText(p.w).width);
            const total = larg.reduce((a, b) => a + b, 0) + esp * (ws.length - 1);
            let xx = x - total / 2;
            const yy = y + li * alt;
            ws.forEach((p, wi) => {
                const tp = item.tempos ? item.tempos[p.i] ?? t0 : t0;
                const u = E.seg(t, tp, tp + 0.28);
                if (u <= 0) {
                    xx += larg[wi] + esp;
                    return;
                }
                const s = (u < 1 ? 0.55 + 0.45 * E.back(u) : 1) * (1 - sai * 0.35);
                const giro = (item.giro ?? 0) + Math.sin(p.i * 2.3 + 1) * 0.025;
                const cor = p.dest ? COR.amarelo : COR[item.cor ?? 'branco'] ?? item.cor;
                g.save();
                g.translate(xx + larg[wi] / 2, yy - tam * 0.35);
                g.rotate(giro * (1 - u * 0.3));
                g.scale(s, s);
                g.globalAlpha = Math.min(1, u * 2) * (1 - sai);
                g.translate(-larg[wi] / 2, tam * 0.35);
                // sombra de papel colado: curta, para baixo e para a direita, como em toda a peça
                g.fillStyle = 'rgba(20,6,26,0.42)';
                g.strokeStyle = 'rgba(20,6,26,0.42)';
                g.lineWidth = tam * 0.2;
                g.strokeText(p.w, tam * 0.045, tam * 0.075);
                g.fillText(p.w, tam * 0.045, tam * 0.075);
                g.strokeStyle = COR.tinta;
                g.lineWidth = tam * 0.17;
                g.strokeText(p.w, 0, 0);
                g.fillStyle = cor;
                g.fillText(p.w, 0, 0);
                g.restore();
                xx += larg[wi] + esp;
            });
        });
        g.restore();
    }

    // Etiqueta escrita à mão num pedaço de papel rasgado (dentro da cena, com a câmera).
    function etiqueta(g, txt, x, y, o = {}) {
        const kit = Palco.kit, tam = o.tam ?? 34;
        g.save();
        g.translate(x, y);
        g.rotate(o.rot ?? 0);
        g.font = `${tam}px "Hand"`;
        const w = kit.textW(g, txt, tam) + tam * 0.9, h = tam * 1.25;
        const chave = 'etq:' + txt + tam + (o.cor ?? '');
        Motion.sprite(chave, { x: -w / 2 - 10, y: -h / 2 - 10, w: w + 20, h: h + 20 }, Palco.env.k * 1.6, (c) => {
            Paper.cutout(c, Paper.roundRect(-w / 2, -h / 2, w, h, 6), o.cor ?? '#fbf3df', chave, { border: 2.2, shadow: 0.22, tex: { alpha: [0.12, 0.25] } });
        }).draw(g);
        kit.hand(g, txt, 0, tam * 0.33, tam, o.tinta ?? '#33306e', { align: 'center', p: o.p ?? 1 });
        g.restore();
    }

    return { titulo, etiqueta, COR };
})();
