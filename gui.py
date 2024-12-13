from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QTextEdit, QLabel, QFileDialog,
                             QProgressBar, QMessageBox, QSplitter)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor
import os
from tabulate import tabulate
from solver import read_file, solve_instance


class SolverThread(QThread):
    """Thread for running the solver without blocking the GUI"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, instance):
        super().__init__()
        self.instance = instance

    def run(self):
        try:
            result = solve_instance(self.instance)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class WSPGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.current_instance = None
        self.solver_thread = None

    def initUI(self):
        """Initialize the user interface"""
        # Set window properties
        self.setWindowTitle('Workflow Satisfiability Problem Solver')
        self.setGeometry(100, 100, 1200, 800)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Create sidebar
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)

        # App title
        title_label = QLabel("WSP Solver")
        title_label.setFont(QFont('Arial', 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title_label)

        # Sidebar buttons
        self.load_button = QPushButton('Load File')
        self.load_button.clicked.connect(self.load_file)
        sidebar_layout.addWidget(self.load_button)

        self.solve_button = QPushButton('Solve')
        self.solve_button.clicked.connect(self.solve_problem)
        self.solve_button.setEnabled(False)
        sidebar_layout.addWidget(self.solve_button)

        self.clear_button = QPushButton('Clear')
        self.clear_button.clicked.connect(self.clear_all)
        sidebar_layout.addWidget(self.clear_button)

        sidebar_layout.addStretch()
        main_layout.addWidget(sidebar)

        # Create right panel with splitter
        splitter = QSplitter(Qt.Vertical)

        # Input section
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_label = QLabel("Input File Content:")
        input_label.setFont(QFont('Arial', 10, QFont.Bold))
        input_layout.addWidget(input_label)

        self.input_text = QTextEdit()
        self.input_text.setReadOnly(True)
        input_layout.addWidget(self.input_text)
        splitter.addWidget(input_widget)

        # Results section
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_label = QLabel("Results:")
        results_label.setFont(QFont('Arial', 10, QFont.Bold))
        results_layout.addWidget(results_label)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)
        splitter.addWidget(results_widget)

        # Add splitter to main layout
        main_layout.addWidget(splitter, stretch=1)

        # Create bottom panel for status and progress
        bottom_panel = QWidget()
        bottom_layout = QVBoxLayout(bottom_panel)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        bottom_layout.addWidget(self.progress_bar)

        # Status bar
        self.status_label = QLabel("Ready")
        bottom_layout.addWidget(self.status_label)

        main_layout.addWidget(bottom_panel)

        # Apply dark theme
        self.apply_dark_theme()

    def apply_dark_theme(self):
        """Apply dark theme to the application"""
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(35, 35, 35))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, Qt.black)

        QApplication.setPalette(dark_palette)

        # Style sheets for components
        button_style = """
            QPushButton {
                background-color: #0D47A1;
                border: none;
                color: white;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1565C0;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #424242;
                color: #757575;
            }
        """

        text_edit_style = """
            QTextEdit {
                background-color: #2D2D2D;
                color: #FFFFFF;
                border: 1px solid #424242;
                border-radius: 4px;
            }
        """

        progress_bar_style = """
            QProgressBar {
                border: 1px solid #424242;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #0D47A1;
            }
        """

        self.load_button.setStyleSheet(button_style)
        self.solve_button.setStyleSheet(button_style)
        self.clear_button.setStyleSheet(button_style)
        self.input_text.setStyleSheet(text_edit_style)
        self.results_text.setStyleSheet(text_edit_style)
        self.progress_bar.setStyleSheet(progress_bar_style)

    def load_file(self):
        """Open file dialog and load selected file"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open File",
            "",
            "Text Files (*.txt);;All Files (*.*)"
        )

        if filename:
            try:
                # Read file content
                with open(filename, 'r') as file:
                    content = file.read()
                    self.input_text.setText(content)

                # Parse instance
                self.current_instance = read_file(filename)
                self.solve_button.setEnabled(True)
                self.status_label.setText(f"Loaded file: {os.path.basename(filename)}")
                self.progress_bar.setValue(0)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")
                self.status_label.setText("Error loading file")

    def solve_problem(self):
        """Solve the WSP instance"""
        if not self.current_instance:
            QMessageBox.warning(self, "Warning", "No problem instance loaded")
            return

        # Clear previous results and update status
        self.results_text.clear()
        self.status_label.setText("Solving...")
        self.progress_bar.setValue(50)
        self.solve_button.setEnabled(False)

        # Create and start solver thread
        self.solver_thread = SolverThread(self.current_instance)
        self.solver_thread.finished.connect(self.handle_solution)
        self.solver_thread.error.connect(self.handle_error)
        self.solver_thread.start()

    def handle_solution(self, result):
        """Handle the solver results"""
        from ortools.sat.python import cp_model

        if result['status'] in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            solution_text = "Solution found:\n\n"
            if result.get('assignments'):
                solution_data = [["s" + str(s), "u" + str(u)] for s, u in result['assignments']]
                solution_text += tabulate(solution_data, headers=['Step', 'User'], tablefmt='grid')
            else:
                solution_text += "No assignments needed"
        else:
            solution_text = "Problem is unsatisfiable"

        self.results_text.setText(solution_text)
        self.status_label.setText("Solved successfully")
        self.progress_bar.setValue(100)
        self.solve_button.setEnabled(True)

    def handle_error(self, error_msg):
        """Handle solver errors"""
        QMessageBox.critical(self, "Error", f"Failed to solve: {error_msg}")
        self.status_label.setText("Error solving problem")
        self.progress_bar.setValue(0)
        self.solve_button.setEnabled(True)

    def clear_all(self):
        """Clear all content and reset GUI"""
        self.input_text.clear()
        self.results_text.clear()
        self.current_instance = None
        self.solve_button.setEnabled(False)
        self.status_label.setText("Ready")
        self.progress_bar.setValue(0)
