window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature) {
            const v = feature && feature.properties ? feature.properties.value : null;
            let color = '#edf8e9';
            if (v >= 4) color = '#006d2c';
            else if (v >= 3) color = '#31a354';
            else if (v >= 2) color = '#74c476';
            else if (v >= 1) color = '#bae4b3';
            return {
                weight: 0.8,
                color: color,
                fillColor: color,
                fillOpacity: 0.7
            };
        }

    }
});