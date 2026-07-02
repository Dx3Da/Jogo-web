#!/usr/bin/env python3
"""
LIXÃO - Servidor do jogo
Backend Python com SQLite3
"""

import sqlite3
import json
import os
import http.server
import socketserver
import socket
import urllib.parse
from pathlib import Path
import random
import webbrowser
import threading
import time

DB_PATH = Path(__file__).parent / "data" / "jogo.db"
STATIC_DIR = Path(__file__).parent

# ==========================================
# 1. BANCO DE DADOS E CONFIGURAÇÕES
# ==========================================


def get_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    # CORREÇÃO: timeout=10 faz o banco esperar em vez de travar se você clicar muito rápido!
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS jogador (
            id INTEGER PRIMARY KEY,
            nome TEXT NOT NULL,
            nivel INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            moedas INTEGER DEFAULT 100,
            energia INTEGER DEFAULT 100,
            energia_max INTEGER DEFAULT 100,
            pos_x INTEGER DEFAULT 5,
            pos_y INTEGER DEFAULT 5,
            area_atual TEXT DEFAULT 'lixao_central',
            dia INTEGER DEFAULT 1,
            hora INTEGER DEFAULT 8
        );
        
        CREATE TABLE IF NOT EXISTS inventario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jogador_id INTEGER,
            item_id TEXT NOT NULL,
            quantidade INTEGER DEFAULT 1,
            FOREIGN KEY (jogador_id) REFERENCES jogador(id),
            UNIQUE(jogador_id, item_id)
        );
        
        CREATE TABLE IF NOT EXISTS robos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jogador_id INTEGER,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL,
            nivel INTEGER DEFAULT 1,
            tarefa TEXT DEFAULT 'idle',
            pos_x INTEGER DEFAULT 0,
            pos_y INTEGER DEFAULT 0,
            area TEXT DEFAULT 'lixao_central',
            durabilidade INTEGER DEFAULT 100,
            FOREIGN KEY (jogador_id) REFERENCES jogador(id)
        );
        
        CREATE TABLE IF NOT EXISTS mapa_tiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            area TEXT NOT NULL,
            x INTEGER NOT NULL,
            y INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            estado TEXT DEFAULT 'normal',
            item_id TEXT,
            quantidade INTEGER DEFAULT 0,
            UNIQUE(area, x, y)
        );
        
        CREATE TABLE IF NOT EXISTS cultivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jogador_id INTEGER,
            area TEXT NOT NULL,
            x INTEGER NOT NULL,
            y INTEGER NOT NULL,
            planta_id TEXT NOT NULL,
            estagio INTEGER DEFAULT 0,
            estagio_max INTEGER DEFAULT 4,
            dia_plantio INTEGER DEFAULT 1,
            regado INTEGER DEFAULT 0,
            FOREIGN KEY (jogador_id) REFERENCES jogador(id)
        );
        
        CREATE TABLE IF NOT EXISTS log_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jogador_id INTEGER,
            tipo TEXT,
            descricao TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        -- NOVA TABELA: Loja com preços dinâmicos
        CREATE TABLE IF NOT EXISTS loja_precos (
            item_id TEXT PRIMARY KEY,
            preco_venda INTEGER NOT NULL
        );
    """)
    conn.commit()
    conn.close()

    # Gera os primeiros preços se a tabela estiver vazia
    _atualizar_precos_loja()

# Atualiza os preços do mercado sempre que o jogador dorme


def _atualizar_precos_loja():
    tabela_precos = {
        'sucata_ferro': (5, 15),
        'sucata_plastico': (3, 10),
        'sucata_eletronico': (15, 35),
        'sucata_rara': (50, 120),
        'cogumelo_mutante': (20, 45),
        'batata_radioativa': (30, 65),
        'girassol_oxidado': (40, 90),
        'fungo_ferrugem': (10, 25)
    }
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM loja_precos")
    for item_id, (min_p, max_p) in tabela_precos.items():
        preco = random.randint(min_p, max_p)
        c.execute(
            "INSERT INTO loja_precos (item_id, preco_venda) VALUES (?, ?)", (item_id, preco))
    conn.commit()
    conn.close()


# ==========================================
# 2. INICIALIZAÇÃO DE JOGADOR E MAPA
# ==========================================

def criar_jogador(nome):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM jogador WHERE nome=?", (nome,))
    row = c.fetchone()
    if row:
        conn.close()
        return row['id']

    c.execute("""INSERT INTO jogador (nome) VALUES (?)""", (nome,))
    jid = c.lastrowid

    itens_iniciais = [
        ('sucata_ferro', 5),
        ('sucata_plastico', 3),
        ('semente_cogumelo_mutante', 2),
        ('ferramenta_picareta', 1),
        ('ferramenta_enxada', 1),
        ('ferramenta_regador', 1),
    ]
    for item_id, qtd in itens_iniciais:
        c.execute("""INSERT INTO inventario (jogador_id, item_id, quantidade)
                     VALUES (?,?,?) ON CONFLICT(jogador_id,item_id)
                     DO UPDATE SET quantidade=quantidade+?""",
                  (jid, item_id, qtd, qtd))

    conn.commit()
    conn.close()
    gerar_mapa_inicial()
    return jid


def gerar_mapa_inicial():
    conn = get_db()
    c = conn.cursor()

    areas = {
        'lixao_central': {'w': 20, 'h': 15, 'tipo_base': 'lixo'},
        'area_limpa_norte': {'w': 15, 'h': 10, 'tipo_base': 'terra'},
        'ferro_velho': {'w': 18, 'h': 12, 'tipo_base': 'lixo_pesado'},
        'oficina': {'w': 12, 'h': 10, 'tipo_base': 'concreto'},
    }

    # Semente fixa para gerar o mesmo mapa inicial sempre
    local_random = random.Random(42)

    for area, cfg in areas.items():
        c.execute("SELECT COUNT(*) as n FROM mapa_tiles WHERE area=?", (area,))
        if c.fetchone()['n'] > 0:
            continue

        for y in range(cfg['h']):
            for x in range(cfg['w']):
                tipo = cfg['tipo_base']
                item_id = None
                qtd = 0

                if area == 'lixao_central':
                    r = local_random.random()
                    if r < 0.12:
                        tipo = 'sucata_ferro'
                        item_id = 'sucata_ferro'
                        qtd = local_random.randint(1, 3)
                    elif r < 0.20:
                        tipo = 'sucata_plastico'
                        item_id = 'sucata_plastico'
                        qtd = local_random.randint(1, 2)
                    elif r < 0.25:
                        tipo = 'sucata_eletronico'
                        item_id = 'sucata_eletronico'
                        qtd = 1
                    elif r < 0.28:
                        tipo = 'obstaculo'

                elif area == 'area_limpa_norte':
                    tipo = 'terra_limpa'

                elif area == 'ferro_velho':
                    r = local_random.random()
                    if r < 0.20:
                        tipo = 'sucata_ferro_pesada'
                        item_id = 'sucata_ferro'
                        qtd = local_random.randint(2, 5)
                    elif r < 0.30:
                        tipo = 'sucata_eletronico'
                        item_id = 'sucata_eletronico'
                        qtd = local_random.randint(1, 3)
                    elif r < 0.35:
                        tipo = 'sucata_rara'
                        item_id = 'sucata_rara'
                        qtd = 1

                elif area == 'oficina':
                    tipo = 'concreto'
                    if x == cfg['w']//2 and y == cfg['h']//2:
                        tipo = 'bancada_trabalho'

                c.execute("""INSERT OR IGNORE INTO mapa_tiles (area, x, y, tipo, item_id, quantidade)
                             VALUES (?,?,?,?,?,?)""",
                          (area, x, y, tipo, item_id, qtd))

    conn.commit()
    conn.close()

# ==========================================
# 3. ROTAS DE ESTADO E AÇÕES (API)
# ==========================================


def get_estado_jogo(jogador_id):
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM jogador WHERE id=?", (jogador_id,))
    jogador = dict(c.fetchone())

    c.execute(
        "SELECT item_id, quantidade FROM inventario WHERE jogador_id=?", (jogador_id,))
    # Retorna como lista para o JS ler fácil
    inventario = [dict(row) for row in c.fetchall()]

    c.execute("SELECT * FROM robos WHERE jogador_id=?", (jogador_id,))
    robos = [dict(r) for r in c.fetchall()]

    area = jogador['area_atual']
    c.execute("SELECT * FROM mapa_tiles WHERE area=?", (area,))
    tiles = [dict(t) for t in c.fetchall()]

    c.execute("SELECT * FROM cultivos WHERE jogador_id=? AND area=?",
              (jogador_id, area))
    cultivos = [dict(cv) for cv in c.fetchall()]

    c.execute("SELECT item_id, preco_venda FROM loja_precos")
    precos_loja = {p['item_id']: p['preco_venda'] for p in c.fetchall()}

    conn.close()
    return {
        'jogador': jogador,
        'inventario': inventario,
        'robos': robos,
        'tiles': tiles,
        'cultivos': cultivos,
        'precos_loja': precos_loja
    }


def executar_acao(jogador_id, acao, params):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM jogador WHERE id=?", (jogador_id,))
    jogador = dict(c.fetchone())
    conn.close()

    resultado = {'sucesso': False,
                 'mensagem': 'Ação não reconhecida.', 'xp': 0}

    if acao == 'quebrar_sucata':
        resultado = _quebrar_sucata(jogador_id, jogador, params)
    elif acao == 'cultivar':
        resultado = _cultivar(jogador_id, jogador, params)
    elif acao == 'regar':
        resultado = _regar(jogador_id, params)
    elif acao == 'colher':
        resultado = _colher(jogador_id, jogador, params)
    elif acao == 'construir_robo':
        resultado = _construir_robo(jogador_id, jogador, params)
    elif acao == 'avancar_dia':
        resultado = _avancar_dia(jogador_id, jogador)
    elif acao == 'mover_area':
        resultado = _mover_area(jogador_id, params)
    elif acao == 'limpar_area':
        resultado = _limpar_area(jogador_id, jogador, params)
    elif acao == 'vender_item':
        resultado = _vender_item(jogador_id, params)
    elif acao == 'comprar_item':
        resultado = _comprar_item(jogador_id, params)
    elif acao == 'upar_robo':
        resultado = _upar_robo(jogador_id, params)
    elif acao == 'resetar_jogo':
        resultado = _resetar_jogo(jogador_id)

    return resultado

# ==========================================
# 4. LÓGICA DAS FERRAMENTAS E JOGABILIDADE
# ==========================================


def _adicionar_item(c, jogador_id, item_id, qtd):
    c.execute("""INSERT INTO inventario (jogador_id, item_id, quantidade)
                 VALUES (?,?,?) ON CONFLICT(jogador_id,item_id)
                 DO UPDATE SET quantidade=quantidade+?""",
              (jogador_id, item_id, qtd, qtd))


def _remover_item(c, jogador_id, item_id, qtd):
    c.execute("SELECT quantidade FROM inventario WHERE jogador_id=? AND item_id=?",
              (jogador_id, item_id))
    row = c.fetchone()
    if not row or row['quantidade'] < qtd:
        return False
    c.execute("UPDATE inventario SET quantidade=quantidade-? WHERE jogador_id=? AND item_id=?",
              (qtd, jogador_id, item_id))
    c.execute("DELETE FROM inventario WHERE jogador_id=? AND item_id=? AND quantidade<=0",
              (jogador_id, item_id))
    return True


def _dar_xp(c, jogador_id, xp):
    c.execute("UPDATE jogador SET xp=xp+? WHERE id=?", (xp, jogador_id))
    c.execute("SELECT xp, nivel FROM jogador WHERE id=?", (jogador_id,))
    row = c.fetchone()
    xp_necessario = row['nivel'] * 100
    if row['xp'] >= xp_necessario:
        novo_nivel = row['nivel'] + 1
        c.execute("""UPDATE jogador SET nivel=?, xp=xp-?, energia_max=energia_max+10, energia=energia_max+10
                     WHERE id=?""", (novo_nivel, xp_necessario, jogador_id))
        return novo_nivel
    return None


def _quebrar_sucata(jogador_id, jogador, params):
    x, y = params.get('x', 0), params.get('y', 0)
    area = jogador['area_atual']

    if jogador['energia'] < 10:
        return {'sucesso': False, 'mensagem': 'Energia insuficiente! Durma para recuperar.'}

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM mapa_tiles WHERE area=? AND x=? AND y=?", (area, x, y))
    tile = c.fetchone()

    if not tile or not tile['item_id']:
        conn.close()
        return {'sucesso': False, 'mensagem': 'Nada para quebrar aqui.'}

    tile = dict(tile)
    item_ganho = tile['item_id']
    qtd_ganho = min(tile['quantidade'], 2)
    xp_ganho = 30 if tile['tipo'] in (
        'sucata_rara', 'sucata_eletronico') else 15

    _adicionar_item(c, jogador_id, item_ganho, qtd_ganho)
    c.execute("UPDATE jogador SET energia=energia-10 WHERE id=?", (jogador_id,))

    nova_qtd = tile['quantidade'] - qtd_ganho
    if nova_qtd <= 0:
        c.execute(
            "UPDATE mapa_tiles SET tipo='lixo', item_id=NULL, quantidade=0 WHERE area=? AND x=? AND y=?", (area, x, y))
    else:
        c.execute("UPDATE mapa_tiles SET quantidade=? WHERE area=? AND x=? AND y=?",
                  (nova_qtd, area, x, y))

    nivel_up = _dar_xp(c, jogador_id, xp_ganho)
    conn.commit()
    conn.close()

    msg = f'+{qtd_ganho} {item_ganho} | +{xp_ganho} XP'
    if nivel_up:
        msg += f' | 🎉 NÍVEL {nivel_up}!'
    return {'sucesso': True, 'mensagem': msg, 'xp': xp_ganho}


def _cultivar(jogador_id, jogador, params):
    x, y = params.get('x', 0), params.get('y', 0)
    semente = params.get('semente', 'semente_cogumelo_mutante')
    area = jogador['area_atual']

    if 'limpa' not in area and area != 'area_limpa_norte':
        return {'sucesso': False, 'mensagem': 'Só é possível cultivar em áreas limpas!'}
    if jogador['energia'] < 5:
        return {'sucesso': False, 'mensagem': 'Energia insuficiente!'}

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT tipo FROM mapa_tiles WHERE area=? AND x=? AND y=?", (area, x, y))
    tile = c.fetchone()

    if not tile or tile['tipo'] not in ('terra_limpa', 'terra_arada'):
        conn.close()
        return {'sucesso': False, 'mensagem': 'Precisa arar a terra primeiro!'}

    c.execute("SELECT id FROM cultivos WHERE area=? AND x=? AND y=?", (area, x, y))
    if c.fetchone():
        conn.close()
        return {'sucesso': False, 'mensagem': 'Já tem algo plantado aqui!'}

    if not _remover_item(c, jogador_id, semente, 1):
        conn.close()
        return {'sucesso': False, 'mensagem': f'Sem {semente} no inventário!'}

    estagio_max = {'semente_cogumelo_mutante': 3, 'semente_batata_radioativa': 4,
                   'semente_girassol_oxidado': 5, 'semente_fungo_ferrugem': 2}.get(semente, 4)

    c.execute("""INSERT INTO cultivos (jogador_id, area, x, y, planta_id, estagio_max, dia_plantio)
                 VALUES (?,?,?,?,?,?,?)""", (jogador_id, area, x, y, semente, estagio_max, jogador['dia']))
    c.execute(
        "UPDATE mapa_tiles SET tipo='terra_plantada' WHERE area=? AND x=? AND y=?", (area, x, y))
    c.execute("UPDATE jogador SET energia=energia-5 WHERE id=?", (jogador_id,))
    _dar_xp(c, jogador_id, 10)

    conn.commit()
    conn.close()
    return {'sucesso': True, 'mensagem': f'Plantou {semente}! +10 XP', 'xp': 10}


def _regar(jogador_id, params):
    x, y = params.get('x', 0), params.get('y', 0)
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT area_atual FROM jogador WHERE id=?", (jogador_id,))
    area = c.fetchone()['area_atual']

    c.execute("UPDATE cultivos SET regado=1 WHERE jogador_id=? AND area=? AND x=? AND y=?",
              (jogador_id, area, x, y))
    afetadas = c.rowcount
    conn.commit()
    conn.close()

    if afetadas:
        return {'sucesso': True, 'mensagem': 'Planta regada! 💧'}
    return {'sucesso': False, 'mensagem': 'Sem planta aqui para regar.'}


def _colher(jogador_id, jogador, params):
    x, y = params.get('x', 0), params.get('y', 0)
    area = jogador['area_atual']
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM cultivos WHERE jogador_id=? AND area=? AND x=? AND y=?",
              (jogador_id, area, x, y))
    cultivo = c.fetchone()

    if not cultivo:
        conn.close()
        return {'sucesso': False, 'mensagem': 'Nada para colher aqui.'}

    cultivo = dict(cultivo)
    if cultivo['estagio'] < cultivo['estagio_max']:
        conn.close()
        return {'sucesso': False, 'mensagem': f'Planta ainda crescendo ({cultivo["estagio"]}/{cultivo["estagio_max"]})'}

    colheitas = {
        'semente_cogumelo_mutante': ('cogumelo_mutante', 3),
        'semente_batata_radioativa': ('batata_radioativa', 2),
        'semente_girassol_oxidado': ('girassol_oxidado', 4),
        'semente_fungo_ferrugem': ('fungo_ferrugem', 5),
    }
    item_id, qtd = colheitas.get(
        cultivo['planta_id'], ('planta_desconhecida', 1))

    _adicionar_item(c, jogador_id, item_id, qtd)
    c.execute("DELETE FROM cultivos WHERE id=?", (cultivo['id'],))
    c.execute(
        "UPDATE mapa_tiles SET tipo='terra_arada' WHERE area=? AND x=? AND y=?", (area, x, y))
    _dar_xp(c, jogador_id, 25)

    conn.commit()
    conn.close()
    return {'sucesso': True, 'mensagem': f'Colheu {qtd}x {item_id}! +25 XP'}


def _construir_robo(jogador_id, jogador, params):
    tipo = params.get('tipo', 'robo_coletor')
    nome = params.get('nome', f'Robô #{tipo}')

    receitas = {
        'robo_coletor': {'sucata_ferro': 5, 'sucata_plastico': 3, 'xp': 50},
        'robo_agricultor': {'sucata_ferro': 4, 'sucata_eletronico': 2, 'cogumelo_mutante': 1, 'xp': 80},
        'robo_minerador': {'sucata_ferro': 8, 'sucata_eletronico': 3, 'sucata_rara': 1, 'xp': 120},
        'robo_limpador': {'sucata_ferro': 6, 'sucata_plastico': 4, 'xp': 60},
    }

    if tipo not in receitas:
        return {'sucesso': False, 'mensagem': 'Tipo de robô desconhecido!'}

    receita = receitas[tipo]
    conn = get_db()
    c = conn.cursor()

    for item_id, qtd_necessaria in receita.items():
        if item_id == 'xp':
            continue
        c.execute(
            "SELECT quantidade FROM inventario WHERE jogador_id=? AND item_id=?", (jogador_id, item_id))
        row = c.fetchone()
        if not row or row['quantidade'] < qtd_necessaria:
            conn.close()
            return {'sucesso': False, 'mensagem': f'Precisa de {qtd_necessaria}x {item_id}!'}

    for item_id, qtd_necessaria in receita.items():
        if item_id == 'xp':
            continue
        _remover_item(c, jogador_id, item_id, qtd_necessaria)

    c.execute("""INSERT INTO robos (jogador_id, nome, tipo, pos_x, pos_y, area)
                 VALUES (?,?,?,?,?,?)""", (jogador_id, nome, tipo, jogador['pos_x'], jogador['pos_y'], jogador['area_atual']))

    _dar_xp(c, jogador_id, receita['xp'])
    conn.commit()
    conn.close()
    return {'sucesso': True, 'mensagem': f'🤖 {nome} construído!'}


def _avancar_dia(jogador_id, jogador):
    conn = get_db()
    c = conn.cursor()

    novo_dia = jogador['dia'] + 1
    c.execute("UPDATE jogador SET dia=?, hora=8, energia=energia_max WHERE id=?",
              (novo_dia, jogador_id))

    # 1. Crescer plantas regadas
    c.execute("""UPDATE cultivos SET estagio=MIN(estagio+1, estagio_max), regado=0
                 WHERE jogador_id=? AND regado=1""", (jogador_id,))

    # 2. Robôs trabalham - CORREÇÃO DE ÁREA: Move o robô para o local do recurso automaticamente
    c.execute("SELECT * FROM robos WHERE jogador_id=?", (jogador_id,))
    robos = c.fetchall()

    itens_coletados = {}

    for robo_row in robos:
        robo = dict(robo_row)
       # Dentro da função _avancar_dia, substitua as linhas de _adicionar_item por isto:

        if robo['tipo'] == 'robo_coletor':
            c.execute(
                "SELECT * FROM mapa_tiles WHERE item_id IN ('sucata_ferro', 'sucata_plastico') AND quantidade > 0 AND area='lixao_central' LIMIT 1")
            alvo = c.fetchone()
            if alvo:
                # O robô coleta itens de acordo com o nível dele!
                qtd_coletada = 1 * robo['nivel']
                _adicionar_item(c, jogador_id, alvo['item_id'], qtd_coletada)
                itens_coletados[alvo['item_id']] = itens_coletados.get(
                    alvo['item_id'], 0) + qtd_coletada
                c.execute(
                    "UPDATE mapa_tiles SET quantidade=quantidade-1 WHERE id=?", (alvo['id'],))
                c.execute("UPDATE robos SET area='lixao_central', pos_x=?, pos_y=?, tarefa='coletando' WHERE id=?",
                          (alvo['x'], alvo['y'], robo['id']))

        elif robo['tipo'] == 'robo_minerador':
            c.execute(
                "SELECT * FROM mapa_tiles WHERE item_id IS NOT NULL AND quantidade > 0 AND area='ferro_velho' LIMIT 1")
            alvo = c.fetchone()
            if alvo:
                qtd_coletada = 1 * robo['nivel']
                _adicionar_item(c, jogador_id, alvo['item_id'], qtd_coletada)
                itens_coletados[alvo['item_id']] = itens_coletados.get(
                    alvo['item_id'], 0) + qtd_coletada
                c.execute(
                    "UPDATE mapa_tiles SET quantidade=quantidade-1 WHERE id=?", (alvo['id'],))
                c.execute("UPDATE robos SET area='ferro_velho', pos_x=?, pos_y=?, tarefa='minerando' WHERE id=?",
                          (alvo['x'], alvo['y'], robo['id']))

    conn.commit()
    conn.close()

    # Ao acordar, a bolsa de valores de sucata vira os preços!
    _atualizar_precos_loja()

    msg = f'☀️ Dia {novo_dia} começou!'
    if itens_coletados:
        itens_str = ', '.join(f'{v}x {k}' for k, v in itens_coletados.items())
        msg += f' Robôs pegaram: {itens_str}'

    return {'sucesso': True, 'mensagem': msg, 'dia': novo_dia}


def _mover_area(jogador_id, params):
    area = params.get('area', 'lixao_central')
    areas_validas = ['lixao_central',
                     'area_limpa_norte', 'ferro_velho', 'oficina']

    if area not in areas_validas:
        return {'sucesso': False, 'mensagem': 'Área inválida!'}

    # CORREÇÃO: Tratamento try/finally para garantir que NUNCA trava
    conn = get_db()
    try:
        c = conn.cursor()
        c.execute(
            "UPDATE jogador SET area_atual=?, pos_x=5, pos_y=5 WHERE id=?", (area, jogador_id))
        conn.commit()
    except Exception as e:
        print(f"Erro no banco: {e}")
        return {'sucesso': False, 'mensagem': 'Erro ao mover de área.'}
    finally:
        conn.close()

    nomes = {'lixao_central': 'Lixão Central', 'area_limpa_norte': 'Área Limpa Norte',
             'ferro_velho': 'Ferro-Velho', 'oficina': 'Oficina'}
    return {'sucesso': True, 'mensagem': f'Viajou para {nomes[area]}!', 'area': area}


def _limpar_area(jogador_id, jogador, params):
    x, y = params.get('x', 0), params.get('y', 0)
    area = jogador['area_atual']
    if jogador['energia'] < 8:
        return {'sucesso': False, 'mensagem': 'Energia insuficiente!'}

    conn = get_db()
    c = conn.cursor()
    c.execute(
        "SELECT tipo FROM mapa_tiles WHERE area=? AND x=? AND y=?", (area, x, y))
    tile = c.fetchone()

    if not tile:
        conn.close()
        return {'sucesso': False, 'mensagem': 'Tile inválido.'}

    if tile['tipo'] == 'terra_limpa':
        c.execute(
            "UPDATE mapa_tiles SET tipo='terra_arada' WHERE area=? AND x=? AND y=?", (area, x, y))
        c.execute("UPDATE jogador SET energia=energia-5 WHERE id=?", (jogador_id,))
        _dar_xp(c, jogador_id, 5)
        conn.commit()
        conn.close()
        return {'sucesso': True, 'mensagem': 'Terra arada! Pronta para plantar. +5 XP'}
    elif tile['tipo'] in ('lixo', 'obstaculo'):
        c.execute(
            "UPDATE mapa_tiles SET tipo='terra_limpa', item_id=NULL, quantidade=0 WHERE area=? AND x=? AND y=?", (area, x, y))
        c.execute("UPDATE jogador SET energia=energia-8 WHERE id=?", (jogador_id,))
        _dar_xp(c, jogador_id, 8)
        conn.commit()
        conn.close()
        return {'sucesso': True, 'mensagem': 'Área limpa! +8 XP.'}

    conn.close()
    return {'sucesso': False, 'mensagem': 'Não é possível limpar aqui.'}


def _comprar_item(jogador_id, params):
    item_id = params.get('item_id')
    qtd = int(params.get('quantidade', 1))

    conn = get_db()
    c = conn.cursor()

    # 1. Checa quantas moedas o jogador tem
    c.execute("SELECT moedas FROM jogador WHERE id=?", (jogador_id,))
    moedas_atuais = c.fetchone()['moedas']

    # 2. Descobre o preço atual do item no mercado
    c.execute("SELECT preco_venda FROM loja_precos WHERE item_id=?", (item_id,))
    row_preco = c.fetchone()

    # Se o item não está no mercado flutuante, definimos um preço fixo para sementes
    if not row_preco:
        precos_sementes = {
            'semente_cogumelo_mutante': 15,
            'semente_batata_radioativa': 25,
            'semente_girassol_oxidado': 35
        }
        preco_base = precos_sementes.get(
            item_id, 999)  # 999 se for item inválido
    else:
        preco_base = row_preco['preco_venda']

    # O preço de compra é 50% maior que o de venda (matemática simples: * 1.5)
    preco_compra = int(preco_base * 1.5)
    custo_total = preco_compra * qtd

    if moedas_atuais < custo_total:
        conn.close()
        return {'sucesso': False, 'mensagem': f'Faltam moedas! Custa {custo_total}.'}

    # 3. Cobra as moedas e entrega o item
    c.execute("UPDATE jogador SET moedas = moedas - ? WHERE id=?",
              (custo_total, jogador_id))
    _adicionar_item(c, jogador_id, item_id, qtd)

    conn.commit()
    conn.close()
    return {'sucesso': True, 'mensagem': f'🛒 Comprou {qtd}x por {custo_total} moedas!'}


def _vender_item(jogador_id, params):
    item_id = params.get('item_id')
    qtd = int(params.get('quantidade', 1))

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT quantidade FROM inventario WHERE jogador_id=? AND item_id=?",
              (jogador_id, item_id))
    row_inv = c.fetchone()
    if not row_inv or row_inv['quantidade'] < qtd:
        conn.close()
        return {'sucesso': False, 'mensagem': 'Você não tem essa quantidade.'}

    c.execute("SELECT preco_venda FROM loja_precos WHERE item_id=?", (item_id,))
    row_preco = c.fetchone()
    if not row_preco:
        conn.close()
        return {'sucesso': False, 'mensagem': 'Item sem valor comercial.'}

    total_ganho = row_preco['preco_venda'] * qtd
    _remover_item(c, jogador_id, item_id, qtd)
    c.execute("UPDATE jogador SET moedas = moedas + ? WHERE id=?",
              (total_ganho, jogador_id))

    conn.commit()
    conn.close()
    return {'sucesso': True, 'mensagem': f'💰 Vendeu e ganhou {total_ganho} moedas!'}


def _upar_robo(jogador_id, params):
    robo_id = params.get('robo_id')

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT nivel FROM robos WHERE id=? AND jogador_id=?",
              (robo_id, jogador_id))
    robo = c.fetchone()

    if not robo:
        conn.close()
        return {'sucesso': False, 'mensagem': 'Robô não encontrado.'}

    nivel_atual = robo['nivel']
    # Nível 1 pro 2 custa 150, do 2 pro 3 custa 300...
    custo_moedas = nivel_atual * 150

    c.execute("SELECT moedas FROM jogador WHERE id=?", (jogador_id,))
    if c.fetchone()['moedas'] < custo_moedas:
        conn.close()
        return {'sucesso': False, 'mensagem': f'Precisa de {custo_moedas} moedas para upar!'}

    c.execute("UPDATE jogador SET moedas = moedas - ? WHERE id=?",
              (custo_moedas, jogador_id))
    c.execute("UPDATE robos SET nivel = nivel + 1 WHERE id=?", (robo_id,))

    conn.commit()
    conn.close()
    return {'sucesso': True, 'mensagem': f'🤖 Robô evoluiu para o Nível {nivel_atual + 1}!'}

# ==========================================
# 5. SERVIDOR WEB HTTP
# ==========================================


class GameHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == '/api/estado':
            params = urllib.parse.parse_qs(parsed.query)
            jid = int(params.get('jogador_id', [1])[0])
            self._json_response(get_estado_jogo(jid))
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/acao/resetar':
            self._json_response(_resetar_banco())
            return

        if self.path.startswith('/api/'):
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length))

            if self.path == '/api/novo_jogo':
                jid = criar_jogador(body.get('nome', 'Jogador'))
                self._json_response({'jogador_id': jid, 'sucesso': True})
            elif self.path == '/api/resetar':
                jid = body.get('jogador_id', 1)
                limpar_dados_banco(jid)
                self._json_response({'sucesso': True})
            elif self.path == '/api/acao':
                jid = body.get('jogador_id', 1)
                acao = body.get('acao')
                params = body.get('params', {})
                self._json_response(executar_acao(jid, acao, params))
            else:
                self._json_response(
                    {'sucesso': False, 'mensagem': 'API inválida.'})
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        # Responde preflight CORS
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers',
                         self.headers.get('Access-Control-Request-Headers', 'Content-Type'))
        self.send_header('Access-Control-Max-Age', '3600')
        self.end_headers()

    def _json_response(self, data):
        resp = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(resp))
        # Cabeçalhos CORS para permitir chamadas do frontend (127.0.0.1 vs localhost)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Max-Age', '3600')
        self.end_headers()
        self.wfile.write(resp)

    def log_message(self, format, *args): pass


def limpar_dados_banco(jid):
    conn = get_db()
    c = conn.cursor()
    # Ordem importante: limpa itens e robôs antes do jogador para evitar erro de Foreign Key
    c.execute("DELETE FROM inventario WHERE jogador_id = ?", (jid,))
    c.execute("DELETE FROM robos WHERE jogador_id = ?", (jid,))
    c.execute(
        "UPDATE jogador SET moedas = 100, energia = 100, dia = 1 WHERE id = ?", (jid,))
    conn.commit()
    conn.close()


def _resetar_banco():
    if DB_PATH.exists():
        try:
            DB_PATH.unlink()
        except OSError:
            pass

    init_db()
    return {'sucesso': True, 'mensagem': 'Banco reiniciado.'}


def _resetar_jogo(jogador_id):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE jogador SET moedas = 0, energia = 100, xp = 0 WHERE id = ?", (jogador_id,))
    c.execute("DELETE FROM inventario WHERE jogador_id = ?", (jogador_id,))
    c.execute("DELETE FROM robos WHERE jogador_id = ?", (jogador_id,))
    c.execute("DELETE FROM cultivos WHERE jogador_id = ?", (jogador_id,))
    conn.commit()
    conn.close()
    return {'sucesso': True, 'mensagem': 'Jogo resetado.'}


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

    def server_bind(self):
        # Tenta ativar SO_REUSEADDR antes de bind para reduzir erros de reutilização
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception:
            pass
        return super().server_bind()


def main():
    init_db()
    gerar_mapa_inicial()
    PORT = 8765

    # Tenta abrir o servidor em várias opções, lidando com PermissionError/porta ocupada
    server = None
    selected_host = None
    selected_port = None

    # Gera lista de portas candidatas (porta padrão e 10 alternativas)
    candidate_ports = [PORT] + list(range(PORT + 1, PORT + 11))
    hosts = ["", "127.0.0.1"]

    for p in candidate_ports:
        for h in hosts:
            try:
                server = ReusableTCPServer((h, p), GameHandler)
                selected_host = h
                selected_port = p
                break
            except PermissionError:
                # Permissão negada — tenta próximo host/porta
                continue
            except OSError:
                # Porta possivelmente em uso — tenta próxima
                continue
        if server:
            break

    if not server:
        print("❌ Não foi possível abrir o socket em nenhuma porta candidata. Verifique permissões e portas em uso.")
        return

    url = f"http://{selected_host or 'localhost'}:{selected_port}"
    print(f"🗑️  LIXÃO - Servidor rodando em {url}")
    print(f"   Pressione Ctrl+C no terminal para desligar.")

    # Função paralela (Thread) para abrir o navegador de forma automática
    def abrir_navegador():
        time.sleep(1)
        webbrowser.open(url)

    threading.Thread(target=abrir_navegador, daemon=True).start()

    try:
        with server as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n👋 Servidor encerrado.")
    finally:
        try:
            server.server_close()
        except Exception:
            pass


if __name__ == '__main__':
    main()
