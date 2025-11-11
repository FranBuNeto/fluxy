# pwf_parser.py
import re

def parse_pwf_file(filepath: str):
    """
    Lê um arquivo .PWF e extrai dados de barras (DBAR) e linhas (DLIN).
    Versão 3: Lida com registros DBAR de múltiplas linhas.
    """
    data = {'title': '', 'buses': [], 'branches': []}
    current_section = None

    with open(filepath, 'r', encoding='latin-1') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        line = lines[i]
        
        if line.startswith('('):
            i += 1
            continue
            
        strip_line = line.strip()
        if not strip_line:
            i += 1
            continue

        if strip_line == 'TITU':
            current_section = 'TITU'
            i += 1
            continue
        elif strip_line == 'DBAR':
            current_section = 'DBAR'
            i += 1
            continue
        elif strip_line == 'DLIN':
            current_section = 'DLIN'
            i += 1
            continue
        elif strip_line == '99999':
            current_section = None
            i += 1
            continue
        elif strip_line == 'FIM':
            break

        if current_section == 'TITU' and not data['title']:
            data['title'] = strip_line
            
        elif current_section == 'DBAR':
            # Checa se a linha é uma barra (tem número nos 5 primeiros chars)
            if line[0:5].strip().isdigit():
                # É uma nova barra. Pega continuação se houver.
                # Limita a 80 cols para não pegar \n e junta com continuação
                full_record_line = line[0:80].rstrip()
                
                if (i + 1) < len(lines):
                    next_line = lines[i+1]
                    # Se prox. linha não for comentário E não for outra barra (não tem num) E não for outra seção
                    if (not next_line.startswith('(') and 
                        not next_line[0:5].strip().isdigit() and
                        next_line.strip() not in ['DLIN', '99999', 'FIM']):
                         
                         # É uma linha de continuação
                         # Adiciona os dados, pulando os espaços em branco iniciais
                         full_record_line += " " + next_line.strip()
                         i += 1 # Pula a linha de continuação
                
                try:
                    bus_data = parse_dbar_line(full_record_line)
                    data['buses'].append(bus_data)
                except Exception as e:
                    print(f"Erro ao ler linha DBAR: {e} | LINHA: {full_record_line.strip()}")
            
        elif current_section == 'DLIN':
            # Linhas DLIN não parecem ter continuação neste formato
            try:
                branch_data = parse_dlin_line(line)
                data['branches'].append(branch_data)
            except Exception as e:
                print(f"Erro ao ler linha DLIN: {e} | LINHA: {line.strip()}")
        
        i += 1
    return data

def parse_dbar_line(line: str):
    """
    Interpreta uma linha da seção DBAR com base no formato fixo.
    (Num)OETGb(   nome   )Gl( V)( A)( Pg)( Qg)( Qn)( Qm)(Bc  )( Pl)( Ql)( Sh)Are
    """
    # Dados da primeira parte da linha
    data = {
        'number': line[0:5].strip(),
        'type': line[5:8].strip(),
        'name': line[8:20].strip(),
        'group': line[20:22].strip(),
        'voltage': line[22:26].strip(),
        'angle': line[26:30].strip(),
        'p_gen': line[30:35].strip(),
        'q_gen': line[35:40].strip(),
        'q_min': line[40:45].strip(),
        'q_max': line[45:50].strip(),
        'shunt_b': line[50:55].strip(),
        'p_load': line[55:60].strip(),
        'q_load': line[60:65].strip(),
        'shunt_sh': line[65:70].strip(),
        'area': line[70:73].strip(),
    }
    
    # Se a linha for longa (continuação), tenta extrair dados dela
    if len(line) > 80:
        continuation = line[80:].strip()
        # Tenta extrair P-load, Q-load, Area da continuação
        # Ex: "623. 22.3     2051000"
        parts = re.split(r'\s+', continuation)
        if len(parts) >= 3:
            # Sobrescreve P e Q Load se estiverem vazios da primeira linha
            if not data['p_load'] and not data['q_load']:
                data['p_load'] = parts[0]
                data['q_load'] = parts[1]
                data['area'] = parts[2] # Pega a área daqui
    
    return data

def parse_dlin_line(line: str):
    """
    Interpreta uma linha da seção DLIN com base no formato fixo.
    (De )d O d(Pa )NcEPM( R% )( X% )(Mvar)(Tap)(Tmn)(Tmx)(Phs)(Bc  )(Cn)(Ce)Ns(Cq)
    """
    return {
        'from_bus': line[0:5].strip(),
        'to_bus': line[10:15].strip(),
        'circuit': line[15:17].strip(),
        'type': line[17:18].strip(), # 'T' para Transformador
        'status': line[18:19].strip(),
        'r': line[21:26].strip(),
        'x': line[26:32].strip(),
        'shunt_b': line[32:38].strip(),
        'tap': line[38:43].strip(),
        'tap_min': line[43:48].strip(),
        'tap_max': line[48:53].strip(),
        'phase': line[53:58].strip(),
    }