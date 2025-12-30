window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature) {
            const c = (feature.properties && feature.properties.color) || '#444';
            return {
                color: c,
                fillColor: c,
                fillOpacity: 0.25,
                weight: 2
            };
        }
    }
});