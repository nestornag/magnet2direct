from simple_magnet2direct import app

# Vercel expects the WSGI application to be called 'app'
# This is the entry point for Vercel
if __name__ == "__main__":
    app.run()
