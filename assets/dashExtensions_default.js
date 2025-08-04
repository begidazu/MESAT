window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(e, ctx) {
            console.log(`You clicked at ${e.latlng}.`)
        }
    }
});