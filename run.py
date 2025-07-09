from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        debug=True,
        host="0.0.0.0",
        port=8050,
        dev_tools_ui=False,            # quita el botón azul de errores
        dev_tools_props_check=False)
