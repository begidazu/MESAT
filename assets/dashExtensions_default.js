window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature, context) {
                const colors = context.props.hideout.colors; // paleta de 5 colores
                const p = feature && feature.properties ? feature.properties : {}; // props
                const cls = parseInt(p.condition_class); // clase 0..5
                if (!cls || cls <= 0) { // 0 o inválido => NoData
                    return {
                        color: 'black',
                        weight: 1,
                        dashArray: '4',
                        fillOpacity: 0.0
                    }; // borde negro, relleno transparente
                }
                const idx = Math.max(0, Math.min(colors.length - 1, cls - 1)); // índice seguro 0..4
                return {
                    fillColor: colors[idx],
                    color: '#ffffff',
                    weight: 0.5,
                    fillOpacity: 0.75
                }; // estilo
            }

            ,
        function1: function(feature, layer, context) {
            const p = feature && feature.properties ? feature.properties : {};
            const v = (p.condition === null || p.condition === undefined) ? 'NoData' : Number(p.condition).toFixed(2);
            const c = (p.confidence === null || p.confidence === undefined) ? 'n/a' : Number(p.confidence).toFixed(2);
            const t = `Condition: ${v} | Confidence: ${c}`;
            layer.bindTooltip(t, {
                sticky: true
            });
        }

    }
});