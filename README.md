# 🗑️ EcoSys - O Jogo

Um jogo de "Simulador de Gerenciamento de Automação Pós-Apocalíptico"
Desenvolvido em **Python 3 + SQLite3** (backend) e **HTML5 Canvas** (frontend).

---

## 📖 Sobre o Projeto

Projeto desenvolvido como parte de um trabalho acadêmico da faculdade, com foco na criação de uma aplicação web interativa utilizando HTML, CSS, JavaScript e Python.

> ⚠️ Este projeto foi desenvolvido em um curto período de tempo para atender aos requisitos da disciplina. O foco principal foi entregar um produto funcional, priorizando a implementação das funcionalidades em vez da arquitetura do código.

### 🤖 Desenvolvimento com IA

Durante o desenvolvimento foram aplicados conceitos como:
- Manipulação do DOM
- Eventos JavaScript
- Atualização dinâmica da interface
- Organização da lógica do jogo
- Integração com Python para persistência de dados
- Estruturação de páginas utilizando HTML e CSS

**Processo de Desenvolvimento com IA:**

1. **Fase Inicial (Claude):** Estabelecimento da arquitetura base do projeto e estrutura fundamental do backend em Python, criação da integração com SQLite3 e geração inicial do frontend com Canvas.

2. **Fase de Aprimoramento (Gemini):** Otimizações iterativas, evolução das mecânicas de jogo, melhorias de performance e refinamento das funcionalidades implementadas.

3. **Execução Manual:** Cada sugestão gerada foi testada, compreendida, adaptada e integrada conforme as necessidades específicas da aplicação. Todo o ciclo de validação, correção de bugs e evolução das features foi realizado manualmente.

**Filosofia:** IA foi utilizada como ferramenta de produtividade para acelerar o desenvolvimento sem sacrificar a qualidade e compreensão do código. O foco foi em entregar um produto funcional e bem estruturado dentro das limitações de tempo do projeto acadêmico.

**Tecnologias Utilizadas:**
- HTML5
- CSS3
- JavaScript
- Python

---

## 🚀 Como Jogar

### Requisitos
- Python 3.8 ou superior
- Bibliotecas nativas: sqlite3, json, http.server
- Navegador: Google Chrome ou Firefox atualizado

### Iniciar
```bash
cd ecosys_game
python3 server.py
```

Abra o navegador em: **http://localhost:8765**

---

## 🎮 Controles

| Ação | Como fazer |
|------|-----------|
| Interagir com tile | Clique esquerdo |
| Mover câmera | Arrastar com botão direito |
| Zoom | Scroll do mouse |

Nota sobre o Design: O jogo utiliza uma interface "Mouse-Only". Não são necessários atalhos de teclado. Basta selecionar a ação no painel de ferramentas e clicar no elemento do mapa com o qual deseja interagir. O jogo processa automaticamente a lógica e compatibilidade da ferramenta com o terreno.

---

## 🛠️ Ferramentas

| Ferramenta | Uso | Custo de energia |
|-----------|-----|-----------------|
| ⛏️ Picareta | Quebra sucata nos tiles | 10 |
| 🧹 Vassoura | Limpa lixo (vira terra limpa) | 8 |
| 🍀 Enxada | Ara terra limpa / Planta sementes | 5 |
| 💧 Regador | Rega plantas | 2 |
| ✋ Mão | Colhe plantas maduras | 3 |

---

## 🗺️ Áreas do Mapa

### 🗑️ Lixão Central
- Área inicial com sucata espalhada
- Use picareta para coletar ferro, plástico e eletrônicos
- Spawn contínuo de sucata

### ⚙️ Ferro-Velho
- Sucata mais densa e valiosa
- Ferro pesado, eletrônicos e **sucata rara**
- Mais difícil de quebrar, mais XP

### 🌿 Área Limpa Norte
- **Sem spawn de lixo** - ambiente controlado
- Use vassoura → enxada → plantar sementes
- Regue todo dia para as plantas crescerem

### 🔧 Oficina
- Área para construir robôs
- Bancada de trabalho no centro

---

## 🤖 Robôs

| Robô | Custo | Função |
|------|-------|--------|
| 🤖 Coletor | 5×Ferro + 3×Plástico | Coleta sucata automaticamente ao dormir |
| 🌾 Agricultor | 4×Ferro + 2×Eletrônico + 1×Cogumelo | Cuida das plantações |
| ⛏ Minerador | 8×Ferro + 3×Eletrônico + 1×Rara | Quebra sucata pesada eficientemente |
| 🧹 Limpador | 6×Ferro + 4×Plástico | Limpa áreas automaticamente |

---

## 🌱 Cultivo

**Só funciona em Áreas Limpas!**

1. Use **vassoura** no lixo → vira terra limpa
2. Use **enxada** na terra limpa → terra arada
3. Selecione a semente no painel e use **enxada** na terra arada → planta
4. Use **regador** todo dia nas plantas
5. Espere os estágios completarem
6. Use **mão** para colher!

### 🌿 Plantas

| Semente | Estágios | Colheita |
|---------|----------|----------|
| 🍄 Cogumelo Mutante | 3 dias | 3× Cogumelo |
| 🥔 Batata Radioativa | 4 dias | 2× Batata |
| 🌻 Girassol Oxidado | 5 dias | 4× Girassol |
| 🟤 Fungo Ferrugem | 2 dias | 5× Fungo |

---

## 📊 Progressão

- **XP** ganho quebrando sucata, cultivando, limpando
- **Nível** sobe a cada 100×nivel XP → mais energia máxima
- **Dormir** restaura energia e avança o dia (robôs trabalham!)

---

## 🗃️ Banco de Dados

SQLite3 salvo em `data/jogo.db`. Tabelas:
- `jogador` - Status, posição, energia, XP
- `inventario` - Itens coletados
- `robos` - Robôs construídos
- `mapa_tiles` - Estado de cada tile do mapa
- `cultivos` - Plantas em crescimento
- `log_eventos` - Histórico de ações

---

## 💡 Dicas

1. Comece quebrando sucata com a picareta para acumular ferro
2. Limpe a Área Limpa Norte e comece a cultivar Fungo Ferrugem (rápido!)
3. Construa um Robô Coletor o mais cedo possível
4. Durma todo dia para os robôs trabalharem e as plantas crescerem
5. Vá ao Ferro-Velho para conseguir sucata rara (necessária para o Robô Minerador)

---

## 🎯 Objetivos de Aprendizado

Este projeto contribuiu para o aprendizado de:

- Estruturação de aplicações web
- Organização da lógica utilizando JavaScript
- Comunicação entre Front-end e Back-end
- Resolução de problemas
- Integração de diferentes tecnologias
- Utilização de IA como apoio ao desenvolvimento

---

## 🔮 Melhorias Futuras

Algumas melhorias que podem ser implementadas futuramente:

- Refatoração completa da estrutura do código
- Separação da lógica em módulos
- Melhor organização dos arquivos
- Interface mais responsiva
- Sistema de salvamento mais robusto
- Melhor desempenho geral
- Documentação técnica

---

## 📚 Status do Projeto

🟡 Finalizado como projeto acadêmico.

O projeto permanece disponível neste repositório como registro da evolução dos meus estudos e poderá receber melhorias futuramente.

---

## 👨‍💻 Autor

Luiz Fernando

Desenvolvido como parte da minha jornada de aprendizado em Desenvolvimento Full Stack.
