# power_system_model.py
import copy
import re

def parse_pwf_float(value: str, default: float = 0.0) -> float:
    """
    Converte um valor float do formato PWF para float padrão.
    Ex: '059-' -> 1.059, ' 994-' -> 0.994, '-25.1' -> -25.1
    """
    val = value.strip()
    if not val:
        return default
    
    # Lógica para 'XXX-' (formato de tensão)
    if val.endswith('-') and len(val) == 4 and val[:-1].strip().isdigit():
        digits = val[:-1].strip()
        # ' 994-' -> '994' -> 0.994
        if val.startswith(' '):
            return float(f"0.{digits}")
        # '059-' -> '059' -> 1.059
        else:
            return float(f"1.{digits}")
    
    # Lógica para notação científica como '59-2' (59e-2) ou '3.-16' (3.0e-16)
    if '-' in val and not val.startswith('-') and not val.endswith('-'):
        try:
            # Substitui o separador por 'e-' para conversão padrão
            scientific_val = val.replace('-', 'e-')
            return float(scientific_val)
        except ValueError:
            pass # Se falhar, continua para a próxima tentativa

    # Caso padrão (números normais, como -25.1 ou 828.)
    try:
        # Remove espaços extras (ex: "1. .837")
        val_clean = re.sub(r'\s+', '', val)
        return float(val_clean)
    except ValueError:
        # Se falhar, como no caso '59-2' que você viu, retorna o padrão
        print(f"Aviso: Não foi possível converter '{value}' para float. Usando {default}.")
        return default

class Bus:
    """ Armazena dados de uma barra (DBAR). """
    def __init__(self, raw_data: dict):
        self.number = int(raw_data['number'])
        self.name = raw_data['name'].strip()
        self.type = raw_data['type']
        
        self.status = True # Ligado por padrão
        # Usa a nova função de parse
        self.voltage = parse_pwf_float(raw_data['voltage'], 1.0)
        self.angle = parse_pwf_float(raw_data['angle'], 0.0)
        self.p_gen = parse_pwf_float(raw_data.get('p_gen', '0.0'))
        self.q_gen = parse_pwf_float(raw_data.get('q_gen', '0.0'))
        self.p_load = parse_pwf_float(raw_data.get('p_load', '0.0'))
        self.q_load = parse_pwf_float(raw_data.get('q_load', '0.0'))
        self.q_min = parse_pwf_float(raw_data.get('q_min', '0.0'))
        self.q_max = parse_pwf_float(raw_data.get('q_max', '0.0'))
        self.shunt_b = parse_pwf_float(raw_data.get('shunt_b', '0.0'))
        
        # Tenta converter 'area', mas não falha se estiver vazio
        area_str = raw_data.get('area', '0').strip()
        self.area = int(area_str) if area_str.isdigit() else 0
        
        # Dados de resultado
        self.v_result = None
        self.angle_result = None

    def __repr__(self):
        return f"<Bus {self.number} - {self.name}>"

class Branch:
    """ Armazena dados de uma linha ou transformador (DLIN). """
    def __init__(self, raw_data: dict):
        self.from_bus = int(raw_data['from_bus'])
        self.to_bus = int(raw_data['to_bus'])
        self.circuit = int(raw_data['circuit'])
        self.is_transformer = raw_data['type'] == 'T'
        
        # Usa a nova função de parse
        self.r = parse_pwf_float(raw_data['r'])
        self.x = parse_pwf_float(raw_data['x'])
        self.shunt_b = parse_pwf_float(raw_data['shunt_b'])
        self.tap = parse_pwf_float(raw_data.get('tap', '1.0'), 1.0)
        self.status = True # Ligado por padrão

    def get_id(self):
        return f"{self.from_bus}-{self.to_bus}-{self.circuit}"

    def __repr__(self):
        tipo = "TR" if self.is_transformer else "LT"
        return f"<{tipo} {self.get_id()} (R={self.r}, X={self.x})>"

class PowerSystem:
    """ Contêiner principal para os dados da rede. """
    def __init__(self):
        self.title = ""
        self.buses = {} # {number: Bus}
        self.branches = {} # {id: Branch}
        self._original_buses = {}
        self._original_branches = {}
        self.results = None
        self.log = ""

    def load_from_pwf(self, pwf_data: dict):
        """ Popula o sistema com dados do parser. """
        self.title = pwf_data.get('title', 'Sem Título')
        self.buses = {}
        self.branches = {}
        
        for b_data in pwf_data['buses']:
            try:
                bus = Bus(b_data)
                self.buses[bus.number] = bus
            except Exception as e:
                print(f"Erro ao criar barra com dados: {b_data} | Erro: {e}")

        for br_data in pwf_data['branches']:
            try:
                branch = Branch(br_data)
                self.branches[branch.get_id()] = branch
            except Exception as e:
                print(f"Erro ao criar ramo com dados: {br_data} | Erro: {e}")
        
        # Guarda cópia de segurança para restauração
        self._original_buses = copy.deepcopy(self.buses)
        self._original_branches = copy.deepcopy(self.branches)
        print(f"Sistema carregado: {len(self.buses)} barras, {len(self.branches)} ramos.")

    def restore_original_data(self):
        """ Restaura os dados para o estado original do arquivo. """
        self.buses = copy.deepcopy(self._original_buses)
        self.branches = copy.deepcopy(self._original_branches)
        self.results = None
        self.log = ""
        print("Dados originais restaurados.")