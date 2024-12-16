# main.py
from views import WSPView
from controllers import WSPController

def main():
    # Create view
    app = WSPView()
    
    # Create controller
    controller = WSPController(app)
    
    # Start application
    app.mainloop()

if __name__ == "__main__":
    main()
    