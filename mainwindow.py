# mainwindow.py
from PyQt6.QtWidgets import (QMainWindow, QToolBar, QFileDialog, QDockWidget, 
                             QTextEdit, QStatusBar, QMessageBox, QToolButton, QMenu)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt, QSize
from power_system_model import PowerSystem
from pwf_parser import parse_pwf_file
from graph_view import InteractiveGraphView
from parameters_panel import ParametersPanel
import solvers

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analisador de Fluxo de Potência")
        self.setGeometry(100, 100, 1200, 800)

        self.system = None
        self.current_solver = 'newton' # Solver padrão

        # Widget Central (Gráfico)
        self.graph_view = InteractiveGraphView(self)
        self.setCentralWidget(self.graph_view)

        # Painel de Parâmetros
        self.params_panel = ParametersPanel(self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.params_panel)

        # Painel de Log
        self.log_dock = QDockWidget("Log de Cálculo", self)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_dock.setWidget(self.log_output)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)

        # Barra de Ferramentas
        self.setup_toolbar()
        
        # Barra de Status
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Pronto. Abra um arquivo .PWF para começar.")

    def setup_toolbar(self):
        toolbar = QToolBar("Ferramentas")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        # --- Ação: Abrir Arquivo ---
        action_open = QAction("Abrir arquivo", self)
        action_open.setStatusTip("Abrir arquivo de rede (.PWF)")
        action_open.triggered.connect(self.open_file)
        toolbar.addAction(action_open)

        toolbar.addSeparator()

        # --- Ação: Escolher Solver ---
        self.solver_button = QToolButton()
        self.solver_button.setText("Solver: Newton-Raphson")
        self.solver_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        solver_menu = QMenu(self)
        
        action_nr = QAction("Newton-Raphson", self)
        action_nr.triggered.connect(lambda: self.set_solver('newton', 'Newton-Raphson'))
        solver_menu.addAction(action_nr)

        action_gs = QAction("Gauss-Seidel", self)
        action_gs.triggered.connect(lambda: self.set_solver('gauss_seidel', 'Gauss-Seidel'))
        solver_menu.addAction(action_gs)
        
        action_g = QAction("Gauss (Jacobi)", self)
        action_g.triggered.connect(lambda: self.set_solver('gauss_jacobi', 'Gauss (Jacobi)'))
        solver_menu.addAction(action_g)

        self.solver_button.setMenu(solver_menu)
        toolbar.addWidget(self.solver_button)
        
        # --- Ação: Parâmetros ---
        action_params = QAction("Parâmetros", self)
        action_params.setStatusTip("Mostrar/Esconder painel de parâmetros")
        action_params.triggered.connect(self.toggle_parameters_panel)
        toolbar.addAction(action_params)

        # --- Ação: Calcular ---
        action_calc = QAction("Calcular", self)
        action_calc.setStatusTip("Executar cálculo de fluxo de potência")
        action_calc.triggered.connect(self.run_calculation)
        toolbar.addAction(action_calc)
        
        # --- Ação: Log ---
        action_log = QAction("Log", self)
        action_log.setStatusTip("Mostrar/Esconder log de cálculo")
        action_log.triggered.connect(self.log_dock.show)
        toolbar.addAction(action_log)

    def set_solver(self, solver_key, solver_name):
        self.current_solver = solver_key
        self.solver_button.setText(f"Solver: {solver_name}")
        self.status_bar.showMessage(f"Solver alterado para {solver_name}.")

    def toggle_parameters_panel(self):
        if self.params_panel.isVisible():
            self.params_panel.hide()
        else:
            self.params_panel.show()

    def open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Abrir Arquivo PWF", "", "Arquivos PWF (*.pwf);;Todos os Arquivos (*)")
        if filepath:
            try:
                self.log_output.clear()
                self.log_output.append(f"Abrindo arquivo: {filepath}\n")
                
                parsed_data = parse_pwf_file(filepath)
                self.system = PowerSystem()
                self.system.load_from_pwf(parsed_data)
                
                self.graph_view.draw_system(self.system)
                self.params_panel.load_system(self.system)
                
                self.log_output.append(f"Sistema '{self.system.title}' carregado com sucesso.")
                self.log_output.append(f"Barras: {len(self.system.buses)}, Ramos: {len(self.system.branches)}")
                self.status_bar.showMessage(f"Sistema '{self.system.title}' carregado.")
            except Exception as e:
                QMessageBox.critical(self, "Erro ao Abrir Arquivo", f"Não foi possível ler o arquivo:\n{e}")
                self.status_bar.showMessage("Erro ao carregar arquivo.")

    def run_calculation(self):
        if not self.system:
            QMessageBox.warning(self, "Nenhum Sistema", "Por favor, abra um arquivo .PWF primeiro.")
            return

        self.status_bar.showMessage("Calculando...")
        self.log_output.append("\n" + "="*30)
        self.log_output.append(f"Iniciando cálculo com solver: {self.current_solver}")

        try:
            # 1. Construir a Matriz Ybus
            ybus, bus_map = solvers.build_ybus(self.system)
            self.log_output.append(f"Matriz Ybus ({ybus.shape[0]}x{ybus.shape[0]}) construída.")
            
            # 2. Chamar o solver selecionado
            success = False
            if self.current_solver == 'newton':
                success = solvers.solve_newton_raphson(self.system, ybus, bus_map)
            elif self.current_solver == 'gauss_seidel':
                success = solvers.solve_gauss_seidel(self.system, ybus, bus_map)
            elif self.current_solver == 'gauss_jacobi':
                success = solvers.solve_gauss_jacobi(self.system, ybus, bus_map)

            # 3. Mostrar log e resultados
            self.log_output.append(self.system.log)
            if success:
                # Adiciona resumo dos resultados ao log
                self.log_output.append("\n--- Matriz de Admitância (Ybus) ---")
                self.log_output.append(str(ybus))
                self.log_output.append("\n--- Resultados Finais ---")
                for bus in self.system.buses.values():
                    if bus.v_result is not None and bus.angle_result is not None:
                        self.log_output.append(
                            f"Barra {bus.number}: V = {bus.v_result:.4f} pu, Ângulo = {bus.angle_result:.3f}°"
                        )

                self.status_bar.showMessage("Cálculo concluído com sucesso.")
                self.log_output.append("Cálculo concluído.")
                
                # Atualiza o painel de parâmetros para destacar os resultados
                self.params_panel.update_results()
                
                # Mostra aviso de conclusão
                QMessageBox.information(self, "Cálculo Concluído", "O cálculo de fluxo de potência foi concluído com sucesso.")

            else:
                self.status_bar.showMessage("Erro no cálculo ou não convergiu.")
                self.log_output.append("Cálculo falhou ou não convergiu.")

        except Exception as e:
            self.status_bar.showMessage("Erro crítico durante o cálculo.")
            self.log_output.append(f"\nERRO CRÍTICO: {e}")
            import traceback
            self.log_output.append(traceback.format_exc())