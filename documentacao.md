# 📚 Documentação do Projeto SaaS: Leitura Diária do Telegram

Este documento consolida a análise de requisitos e o fluxo de trabalho do sistema de envio de leitura bíblica diária via Telegram, desenvolvido em FastAPI/Python no ambiente Termux.

---

## I. Arquivos e Ecossistema (Análise de Composição)

O sistema é composto por quatro arquivos essenciais e duas pastas vitais para o fluxo de trabalho.

### 1. Arquivos de Código e Configuração

| Nome do Arquivo | Função Principal | Uso no Fluxo |
| :--- | :--- | :--- |
| **`main.py`** | **Servidor/Motor.** Inicia o Uvicorn/FastAPI e registra as rotas. | Inicializa a aplicação web. |
| **`adicionar_ocr.py`** | **Gateway de Upload.** Define a rota `/upload_e_processar`, recebe a imagem, salva em `uploads/` e chama a rotina de processamento. | Essencial para o envio mensal da imagem de leitura. |
| **`enviar_leitura_telegram.py`** | **Lógica de Negócios.** Contém o script principal que faz: OCR, pré-processamento, filtro de referências, renomeação de arquivos, e envio da mensagem. | Executado no upload e pelo Cron Job diário. |
| **`.env`** | **Configuração.** Armazena credenciais (TOKENS) e IDs de destino do Telegram. | Segurança e configuração. |

### 2. Pastas (Diretórios)

| Nome da Pasta | Função Principal |
| :--- | :--- |
| **`uploads/`** | Armazena a imagem padronizada do mês atual (ex: `leitura_2025_11_novembro.png`) e é o local de leitura do Cron Job. |
| **`uploads/processadas/`** | Armazena imagens de meses anteriores, movidas automaticamente pelo script para fins de organização. |

---

## II. Fluxo de Trabalho e Configuração (Rotina Diária e Mensal)

### 1. Estratégia de Envio da Imagem (Mensal)

| Ação | Detalhe |
| :--- | :--- |
| **O que enviar?** | Uma única imagem contendo a leitura de **todos os dias do mês**. |
| **Frequência de Envio** | **Mensal.** Enviar a nova imagem do mês seguinte logo após o dia 1º, ou no final do mês anterior. |
| **Ação do Script** | O script irá: 1. Processar a imagem. 2. Assumir o mês atual (por causa do fallback de OCR). 3. **Sobrescrever** o arquivo padronizado (`leitura_YYYY_MM_mes.png`). |
| **Rolagem do Mês** | No primeiro dia do mês novo, o script move a imagem do mês anterior de `uploads/` para `uploads/processadas/`. |

### 2. Configuração de Agendamento (Cron Job)

O script deve ser executado diariamente para verificar a leitura do `hoje_dia`.

* **Comando no Crontab:**
    ```crontab
    # Roda todos os dias às 7:00 da manhã
    0 7 * * * cd /data/data/com.termux/files/home/Biblia_Desktop_FastAPI && python3 enviar_leitura_telegram.py
    ```
    (Note: É mais seguro rodar o `enviar_leitura_telegram.py` diretamente, pois é o script que contém a função `main()` para execução agendada).

* **Para rodar às 6:00 am:**
    ```crontab
    0 6 * * * cd /data/data/com.termux/files/home/Biblia_Desktop_FastAPI && python3 enviar_leitura_telegram.py
    ```

---

## III. Análise de Requisitos para o SaaS

### A. Requisitos Funcionais (O que o Usuário pode Fazer)

| Categoria | Requisito Funcional |
| :--- | :--- |
| **Autenticação** | Cadastro/Login de Usuário, Recuperação de Senha. |
| **Onboarding** | **Integração do Telegram** (usuário vincula o CHAT\_ID com o sistema). |
| | **Configuração de Horário** (usuário define o horário diário de envio). |
| **Upload** | Permitir o **Upload de Imagem Mensal** na Dashboard. |
| **Entrega** | **Disparo Diário Agendado** no horário configurado (Substituindo o Cron Job do Termux por um serviço de fila). |

### B. Requisitos de Infraestrutura e Não Funcionais (SaaS)

| Categoria | Requisito Não Funcional |
| :--- | :--- |
| **Performance** | Envio da mensagem concluído em menos de 5 segundos após o horário agendado. |
| **Segurança** | Armazenamento criptografado de Tokens do Telegram e dados de usuário. |
| **Escalabilidade** | Migração do Cron para um **Serviço de Fila Distribuída** (Celery/Redis) para gerenciar milhares de usuários. |
| **Tecnologia** | Migração do ambiente Termux para um ambiente de produção (Docker/Cloud). |

### C. Requisitos de Negócio e Monetização

| Categoria | Requisito de Negócio |
| :--- | :--- |
| **Monetização** | **Integração de Pagamento** (Stripe, PagSeguro) para aceitar cobranças recorrentes. |
| | **Planos de Assinatura** (Básico/Premium). |
| **Legal** | Criação de Termos de Serviço e Política de Privacidade. |
