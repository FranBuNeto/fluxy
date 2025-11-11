# solvers.py
import numpy as np
import scipy.sparse as sparse
from power_system_model import PowerSystem

def build_ybus(system: PowerSystem):
    """
    Constrói a matriz de admitância (Ybus) do sistema.
    
    NOTA: Esta é uma versão simplificada. Ela não trata
    corretamente transformadores defasadores ou com taps complexos.
    Baseia-se nas fórmulas de Ybus do "Anotações 20102025.pdf".
    """
    
    # Mapeia números de barra (ex: 458) para índices de matriz (ex: 0, 1, 2...)
    # Considera apenas barras ativas
    active_buses = {num: bus for num, bus in system.buses.items() if bus.status}
    bus_numbers = sorted(active_buses.keys())

    bus_map = {bus_num: idx for idx, bus_num in enumerate(bus_numbers)}
    n = len(bus_numbers)
    
    # Usar matriz esparsa para eficiência
    Ybus = sparse.lil_matrix((n, n), dtype=complex)
    
    # 1. Adicionar ramos (Linhas/TRs)
    for branch in system.branches.values():
        if not branch.status: # Ignora ramos desligados
            continue
            
        if branch.from_bus not in bus_map or branch.to_bus not in bus_map:
            print(f"Aviso: Ramo {branch.get_id()} conecta a barra desconhecida.")
            continue
            
        # Índices da matriz
        i = bus_map[branch.from_bus]
        j = bus_map[branch.to_bus]
        
        # Admitância série
        y_series = 1 / (branch.r + 1j * branch.x)
        
        # Admitância shunt (dividida por 2, p/ modelo PI)
        y_shunt = 1j * branch.shunt_b
        
        # TODO: Implementar lógica de TAP do transformador
        # tap = branch.tap if branch.is_transformer else 1.0
        # ... lógica mais complexa aqui ...
        
        # Elementos fora da diagonal (Yij)
        Ybus[i, j] -= y_series
        Ybus[j, i] -= y_series
        
        # Elementos da diagonal (Yii)
        Ybus[i, i] += y_series + (y_shunt / 2)
        Ybus[j, j] += y_series + (y_shunt / 2)

    # 2. Adicionar shunts das barras (DBAR)
    for bus in active_buses.values():
        if bus.shunt_b != 0:
            idx = bus_map[bus.number]
            Ybus[idx, idx] += 1j * bus.shunt_b
            
    # Converter para formato CSC (Compressed Sparse Column) para cálculos rápidos
    return Ybus.tocsc(), bus_map

def solve_gauss_seidel(system: PowerSystem, ybus, bus_map, max_iter=100, tolerance=1e-5):
    """
    Executa o solver Gauss-Seidel.
    Baseado na Equação (20) de "Anotações 20102025.pdf".
    """
    log = "Iniciando Solver Gauss-Seidel...\n"
    print(log.strip())
    
    # TODO: Implementar o loop iterativo de Gauss-Seidel
    # 1. Inicializar V com valores das barras
    # 2. Iterar k = 1 to max_iter:
    # 3.   Para cada barra PQ e PV:
    # 4.     Calcular Vk(i+1) usando a Eq. (20)
    # 5.     Para barras PV, recalcular Q e verificar limites Qmin/Qmax
    # 6.     Verificar convergência (max |Vk(i+1) - Vk(i)|)
    # 7.   Se convergir, parar.
    # 8. Atualizar system.buses com resultados
    
    log += f"Solver (Gauss-Seidel) executado (placeholder).\n"
    log += f"Convergência não implementada.\n"
    
    system.log = log
    return True # Sucesso (simulado)

def solve_newton_raphson(system: PowerSystem, ybus, bus_map, max_iter=20, tolerance=1e-5):
    """
    Executa o solver Newton-Raphson.
    Baseado nas equações do "Exemplo Fluxo.pdf" (pág 31+).
    """
    log = "Iniciando Solver Newton-Raphson...\n"
    print(log.strip())

    # TODO: Implementar o loop iterativo de Newton-Raphson
    # 1. Inicializar V e Ângulo
    # 2. Iterar k = 1 to max_iter:
    # 3.   Calcular Mismatch (dP, dQ)
    # 4.   Verificar convergência (max(dP, dQ) < tolerance)
    # 5.   Construir Matriz Jacobiana (H, N, M, L)
    # 6.   Resolver sistema linear: J * [dAngle, dV] = [dP, dQ]
    # 7.   Atualizar V e Ângulo: V = V + dV, Angle = Angle + dAngle
    # 8. Atualizar system.buses com resultados
    
    # Exemplo de resultado simulado (baseado no "Exemplo Fluxo.pdf" Caso 1)
    if 5 in bus_map: 
        system.buses[454].v_result = 0.994
        system.buses[454].angle_result = -41.380
    
    log += f"Iteração 1: Max Mismatch = 150.0 MW\n"
    log += f"Iteração 2: Max Mismatch = 25.5 MW\n"
    log += f"Iteração 3: Max Mismatch = 3.1 MW\n"
    log += f"Iteração 4: Max Mismatch = 0.2 MW\n"
    log += f"Iteração 5: Max Mismatch = 0.001 MW\n"
    log += f"Solver (Newton-Raphson) convergiu em 5 iterações (simulado).\n"
    
    system.log = log
    system.results = "Concluído (Simulado)"
    return True # Sucesso (simulado)

def solve_gauss_jacobi(system: PowerSystem, ybus, bus_map, max_iter=100, tolerance=1e-5):
    """
    Executa o solver Gauss (Jacobi).
    Baseado na Equação (18) de "Anotações 20102025.pdf".
    """
    log = "Iniciando Solver Gauss (Jacobi)...\n"
    print(log.strip())
    
    # TODO: Implementar o loop iterativo de Gauss (Jacobi)
    # Similar ao Gauss-Seidel, mas usa V(i) para *todos* os termos
    # da somatória, sem usar os valores V(i+1) recém-calculados.
    
    log += f"Solver (Gauss-Jacobi) executado (placeholder).\n"
    log += f"Convergência não implementada.\n"
    
    system.log = log
    return True # Sucesso (simulado)