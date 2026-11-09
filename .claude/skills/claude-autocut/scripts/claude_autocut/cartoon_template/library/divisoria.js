// Divisória do modo podcast-animado: uma tira de papel rasgado em duas camadas (creme por baixo,
// branco por cima), com fibras, textura leve e sombra curta sobre o vídeo. É fixa: pintada uma vez,
// com semente, e nunca muda entre quadros. Global: Divisoria.
//
// o = { canvas, semente, espessura, largura }   (canvas em pixels; a tira fica no meio da altura dele)
const Divisoria = (() => {
    function borda(semente, x0, x1, y, amp, fino, passo = 5) {
        const pts = [];
        for (let x = x0; x <= x1; x += passo) {
            pts.push([x, y + Motion.noise1(semente, x * 0.011) * amp + Motion.noise1(semente + ':f', x * 0.075) * fino]);
        }
        return pts;
    }

    function tira(g, semente, cy, esp, cor, ampCima, ampBaixo, o = {}) {
        const L = g.canvas.width;
        const cima = borda(semente + ':cima', -30, L + 30, cy - esp / 2, ampCima, 1.6);
        const baixo = borda(semente + ':baixo', -30, L + 30, cy + esp / 2, ampBaixo, 2.4).reverse();
        const poly = [...cima, ...baixo];
        if (o.sombra) {
            for (const [dy, a] of [[7, 0.18], [4, 0.22]]) {
                g.save();
                g.translate(1.5, dy);
                g.fillStyle = `rgba(16,6,22,${a})`;
                Paper.tracePath(g, poly);
                g.fill();
                g.restore();
            }
        }
        Paper.cutout(g, poly, cor, semente, { border: 0, shadow: 0, jag: 1.1, step: 2, tex: { alpha: [0.06, 0.16], lVar: 2.2, sVar: 1, len: [30, 90], h: [4, 9] } });
        // fibras soltas na borda rasgada de baixo
        const r = Paper.rng(semente + ':fib');
        g.strokeStyle = cor;
        g.lineWidth = 0.9;
        g.lineCap = 'round';
        g.beginPath();
        for (const [x, y] of baixo) {
            if (r() > 0.22) continue;
            const l = 1.5 + r() * 3.5;
            g.moveTo(x, y);
            g.lineTo(x + (r() - 0.5) * 2.5, y + l);
        }
        g.stroke();
    }

    function desenhar(canvas, o = {}) {
        const g = canvas.getContext('2d');
        g.clearRect(0, 0, canvas.width, canvas.height);
        const cy = canvas.height / 2, esp = o.espessura ?? 30, s = o.semente ?? 'divisoria';
        // camada de baixo, creme, um pouco mais larga: aparece como uma segunda folha rasgada
        tira(g, s + ':creme', cy + 3, esp + 10, '#eadfc8', 4, 7, { sombra: true });
        // camada de cima, branca, mais estreita e com outro rasgo
        tira(g, s + ':branca', cy - 1, esp, '#fbf8f0', 3.5, 5.5);
        // risco de lápis bem leve ao longo da tira: acabamento de papel, não chama atenção
        g.save();
        g.globalAlpha = 0.18;
        Paper.markerStroke(g, [[40, cy + 2], [canvas.width * 0.45, cy + 1], [canvas.width - 40, cy + 3]], '#b9ab92', 1.4, s + ':lapis', 1);
        g.restore();
    }

    return { desenhar };
})();
