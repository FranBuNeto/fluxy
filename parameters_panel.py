# parameters_panel.py
from PyQt6.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QTabWidget, 
                             QTableWidget, QTableWidgetItem, QPushButton,
                             QAbstractItemView, QHeaderView, QCheckBox,
                             QHBoxLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

class ParametersPanel(QDockWidget):
    """ Painel para visualização e manipulação dos dados. """
    def __init__(self, parent=None):
        super().__init__("Parâmetros do Sistema", parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.system = None
        self.highlight_color = QColor(200, 230, 255) # Azul claro para destaque
        
        # Widget principal
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        
        # Abas
        self.tabs = QTabWidget()
        self.bus_table = QTableWidget()
        self.branch_table = QTableWidget()
        
        self.tabs.addTab(self.bus_table, "Barras")
        self.tabs.addTab(self.branch_table, "Ramos (Linhas/TRs)")
        layout.addWidget(self.tabs)
        
        # Botão de Restaurar
        self.restore_btn = QPushButton("Restaurar Dados Originais")
        self.restore_btn.clicked.connect(self.on_restore)
        layout.addWidget(self.restore_btn)
        
        self.setWidget(main_widget)
        self.setup_tables()

    def setup_tables(self):
        for table in [self.bus_table, self.branch_table]:
            table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
            table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)            
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setStretchLastSection(True)

    def load_system(self, system):
        self.system = system
        self.populate_bus_table()
        self.populate_branch_table()

    def populate_bus_table(self):
        headers = ["Status", "Num", "Nome", "Tipo", "V (pu)", "Ang (°)", "P Carga", "Q Carga", "P Ger", "Q Ger"]
        self.bus_table.setRowCount(len(self.system.buses))
        self.bus_table.setColumnCount(len(headers))
        self.bus_table.setHorizontalHeaderLabels(headers)

        for i, bus in enumerate(self.system.buses.values()):
            # Checkbox de Status
            checkbox = self._create_checkbox(bus.status, lambda state, b=bus: self._toggle_bus_status(state, b))
            self.bus_table.setCellWidget(i, 0, checkbox)

            self.bus_table.setItem(i, 1, QTableWidgetItem(str(bus.number)))
            self.bus_table.setItem(i, 2, QTableWidgetItem(bus.name))
            self.bus_table.setItem(i, 3, QTableWidgetItem(bus.type))
            self.bus_table.setItem(i, 4, QTableWidgetItem(f"{bus.voltage:.4f}"))
            self.bus_table.setItem(i, 5, QTableWidgetItem(f"{bus.angle:.3f}"))
            self.bus_table.setItem(i, 6, QTableWidgetItem(str(bus.p_load)))
            self.bus_table.setItem(i, 7, QTableWidgetItem(str(bus.q_load)))
            self.bus_table.setItem(i, 8, QTableWidgetItem(str(bus.p_gen)))
            self.bus_table.setItem(i, 9, QTableWidgetItem(str(bus.q_gen)))
        
        self.bus_table.resizeColumnsToContents()

    def populate_branch_table(self):
        headers = ["Status", "ID", "De", "Para", "Tipo", "R (pu)", "X (pu)", "Tap"]
        self.branch_table.setRowCount(len(self.system.branches))
        self.branch_table.setColumnCount(len(headers))
        self.branch_table.setHorizontalHeaderLabels(headers)

        for i, branch in enumerate(self.system.branches.values()):
            tipo = "TR" if branch.is_transformer else "LT"
            
            # Checkbox de Status
            checkbox = self._create_checkbox(branch.status, lambda state, br=branch: self._toggle_branch_status(state, br))
            self.branch_table.setCellWidget(i, 0, checkbox)

            self.branch_table.setItem(i, 1, QTableWidgetItem(branch.get_id()))
            self.branch_table.setItem(i, 2, QTableWidgetItem(str(branch.from_bus)))
            self.branch_table.setItem(i, 3, QTableWidgetItem(str(branch.to_bus)))
            self.branch_table.setItem(i, 4, QTableWidgetItem(tipo))
            self.branch_table.setItem(i, 5, QTableWidgetItem(f"{branch.r:.5f}"))
            self.branch_table.setItem(i, 6, QTableWidgetItem(f"{branch.x:.5f}"))
            self.branch_table.setItem(i, 7, QTableWidgetItem(str(branch.tap)))

        self.branch_table.resizeColumnsToContents()

    def _create_checkbox(self, is_checked, connect_func):
        """Cria um widget de checkbox centralizado."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        checkbox = QCheckBox()
        checkbox.setChecked(is_checked)
        checkbox.stateChanged.connect(connect_func)
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0,0,0,0)
        widget.setLayout(layout)
        return widget

    def _toggle_bus_status(self, state, bus):
        bus.status = (state == Qt.CheckState.Checked.value)
        print(f"Barra {bus.number} status alterado para: {bus.status}")

    def _toggle_branch_status(self, state, branch):
        branch.status = (state == Qt.CheckState.Checked.value)
        print(f"Ramo {branch.get_id()} status alterado para: {branch.status}")

    def update_results(self):
        """Atualiza a tabela de barras com os resultados e destaca as mudanças."""
        if not self.system:
            return

        # Mapeia número da barra para a linha da tabela
        bus_row_map = {int(self.bus_table.item(i, 1).text()): i for i in range(self.bus_table.rowCount())}

        for bus_num, bus in self.system.buses.items():
            if bus_num not in bus_row_map:
                continue
            
            row = bus_row_map[bus_num]
            
            # Atualiza e destaca Tensão
            if bus.v_result is not None:
                item_v = self.bus_table.item(row, 4)
                item_v.setText(f"{bus.v_result:.4f}")
                # Compara com o valor original para destacar
                if abs(bus.v_result - self.system._original_buses[bus_num].voltage) > 1e-4:
                    item_v.setBackground(self.highlight_color)

            # Atualiza e destaca Ângulo
            if bus.angle_result is not None:
                item_a = self.bus_table.item(row, 5)
                item_a.setText(f"{bus.angle_result:.3f}")
                # Compara com o valor original para destacar
                if abs(bus.angle_result - self.system._original_buses[bus_num].angle) > 1e-4:
                    item_a.setBackground(self.highlight_color)

    def on_restore(self):
        if self.system:
            self.system.restore_original_data()
            self._clear_highlights()
            self.load_system(self.system) # Recarrega tabelas
            print("Dados restaurados e destaques limpos.")

    def _clear_highlights(self):
        """Remove o destaque de fundo de todas as células."""
        default_color = QColor(Qt.GlobalColor.transparent)
        for row in range(self.bus_table.rowCount()):
            # Colunas de Tensão (4) e Ângulo (5)
            self.bus_table.item(row, 4).setBackground(default_color)
            self.bus_table.item(row, 5).setBackground(default_color)

    # TODO: Implementar 'on_cell_changed' para atualizar o self.system
    # quando o usuário editar um valor na tabela.