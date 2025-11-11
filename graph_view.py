# graph_view.py
import networkx as nx
from PyQt6.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsRectItem, 
                             QGraphicsLineItem, QGraphicsTextItem, QGraphicsSimpleTextItem,
                             QGraphicsItem, QMenu, QDialog, QVBoxLayout, 
                             QLabel, QDialogButtonBox)
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor, QBrush, QPen
from power_system_model import PowerSystem, Bus, Branch

BUS_COLOR = QColor("#42a5f5")
BUS_COLOR_REF = QColor("#f44336")
BUS_COLOR_PV = QColor("#66bb6a")
LINE_COLOR = QColor("#9e9e9e")

class InfoPanel(QDialog):
    """ Painel flutuante que mostra informações do item. """
    def __init__(self, item_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Informações do Componente")
        self.setWindowModality(Qt.WindowModality.NonModal)

        layout = QVBoxLayout(self)
        if isinstance(item_data, Bus):
            self.build_bus_info(layout, item_data)
        elif isinstance(item_data, Branch):
            self.build_branch_info(layout, item_data)

        # Botão OK
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def build_bus_info(self, layout, bus: Bus):
        layout.addWidget(QLabel(f"<b>Barra: {bus.number} - {bus.name}</b>"))
        layout.addWidget(QLabel(f"Tipo: {bus.type}"))
        layout.addWidget(QLabel(f"Tensão (V): {bus.voltage} pu"))
        layout.addWidget(QLabel(f"Ângulo (A): {bus.angle} °"))
        layout.addWidget(QLabel(f"Carga (Pl/Ql): {bus.p_load} MW / {bus.q_load} MVAr"))
        layout.addWidget(QLabel(f"Geração (Pg/Qg): {bus.p_gen} MW / {bus.q_gen} MVAr"))

    def build_branch_info(self, layout, branch: Branch):
        tipo = "Transformador" if branch.is_transformer else "Linha"
        layout.addWidget(QLabel(f"<b>{tipo}: {branch.get_id()}</b>"))
        layout.addWidget(QLabel(f"De: {branch.from_bus} -> Para: {branch.to_bus}"))
        layout.addWidget(QLabel(f"Status: {'Ligado' if branch.status else 'Desligado'}"))
        layout.addWidget(QLabel(f"R: {branch.r} pu"))
        layout.addWidget(QLabel(f"X: {branch.x} pu"))
        layout.addWidget(QLabel(f"Shunt (B): {branch.shunt_b} pu"))
        if branch.is_transformer:
            layout.addWidget(QLabel(f"Tap: {branch.tap}"))


class BranchItem(QGraphicsLineItem):
    """ Item gráfico para Linhas e Transformadores. """
    def __init__(self, branch: Branch, bus_items: dict):
        super().__init__()
        self.branch = branch
        self.bus_item_from = bus_items[branch.from_bus]
        self.bus_item_to = bus_items[branch.to_bus]

        pen_style = Qt.PenStyle.DashLine if branch.is_transformer else Qt.PenStyle.SolidLine
        self.setPen(QPen(LINE_COLOR, 2, pen_style))
        self.setZValue(-1) # Envia para trás das barras
        self.update_position()

    def update_position(self):
        # --- CORREÇÃO AQUI ---
        # A função setLine espera 4 floats (x1, y1, x2, y2)
        # ou um objeto QLineF.
        # O .scenePos() retorna QPointF. Nós extraímos os valores .x() e .y()
        p1 = self.bus_item_from.scenePos()
        p2 = self.bus_item_to.scenePos()
        
        # Passamos os 4 floats em vez de 2 QPointF
        self.setLine(p1.x(), p1.y(), p2.x(), p2.y())


class BusItem(QGraphicsRectItem):
    """ Item gráfico para Barras. """
    def __init__(self, bus: Bus):
        super().__init__(-15, -15, 30, 30) # Quadrado de 30x30
        self.bus = bus
        self.lines = []
        
        # Define cor baseada no tipo (simplificado)
        if '2' in bus.type: # Ref (ex: L2)
            color = BUS_COLOR_REF
        elif '1' in bus.type: # PV (ex: L1)
            color = BUS_COLOR_PV
        else: # PQ
            color = BUS_COLOR
        
        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.GlobalColor.black, 1))
        
        # Flags
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges, True)

        # Rótulo
        self.label = QGraphicsSimpleTextItem(str(bus.number))
        self.label.setParentItem(self)
        self.label.setPos(-self.label.boundingRect().width() / 2, 15)

    def add_line(self, line_item):
        self.lines.append(line_item)

    def itemChange(self, change, value):
        """ Atualiza linhas ao mover a barra. """
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for line in self.lines:
                line.update_position()
        return value

class InteractiveGraphView(QGraphicsView):
    """ O widget de visualização principal. """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(self.renderHints().Antialiasing)
        self.bus_items = {} # {bus_number: BusItem}
        self.branch_items = {} # {branch_id: BranchItem}
        self.info_panel = None
        
        self.scene.selectionChanged.connect(self.on_selection_changed)

    def clear_system(self):
        self.scene.clear()
        self.bus_items.clear()
        self.branch_items.clear()

    def draw_system(self, system: PowerSystem):
        self.clear_system()
        
        if not system.buses:
            return

        # 1. Usar NetworkX para calcular um layout inicial
        G = nx.Graph()
        G.add_nodes_from(system.buses.keys())
        G.add_edges_from([(br.from_bus, br.to_bus) for br in system.branches.values()])
        
        # Layout de mola: dá posições iniciais para evitar sobreposição
        pos = nx.spring_layout(G, k=1.5, iterations=50, seed=42)

        # 2. Adicionar Barras (BusItem) à cena
        for bus_num, bus in system.buses.items():
            item = BusItem(bus)
            if bus_num in pos:
                # Escala o layout para o tamanho da cena
                item.setPos(pos[bus_num][0] * 500, pos[bus_num][1] * 500)
            else:
                item.setPos(0, 0) # Posição padrão se for barra isolada
            self.scene.addItem(item)
            self.bus_items[bus_num] = item

        # 3. Adicionar Ramos (BranchItem) à cena
        for branch_id, branch in system.branches.items():
            if branch.from_bus in self.bus_items and branch.to_bus in self.bus_items:
                item = BranchItem(branch, self.bus_items)
                self.scene.addItem(item)
                self.branch_items[branch_id] = item
                
                # Informa às barras quais linhas estão conectadas
                self.bus_items[branch.from_bus].add_line(item)
                self.bus_items[branch.to_bus].add_line(item)
        
        self.centerOn(self.bus_items[list(system.buses.keys())[0]])

    def on_selection_changed(self):
        """ Mostra o painel flutuante quando um item é selecionado. """
        selected = self.scene.selectedItems()
        if not selected:
            if self.info_panel:
                self.info_panel.close()
            return

        item = selected[0]
        data = None
        
        if isinstance(item, BusItem):
            data = item.bus
        elif isinstance(item, BranchItem):
            data = item.branch
            
        if data:
            # Fecha painel antigo se existir
            if self.info_panel and self.info_panel.isVisible():
                self.info_panel.close()
                
            self.info_panel = InfoPanel(data, self)
            self.info_panel.show()