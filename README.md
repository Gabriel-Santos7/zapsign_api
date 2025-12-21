# ZapSign API

## 📋 Resumo Executivo

API RESTful desenvolvida em Django para gerenciamento de documentos e assinaturas digitais, com integração à API ZapSign e análise inteligente de conteúdo utilizando IA (spaCy e Google Gemini). A solução implementa uma arquitetura limpa (Clean Architecture) com separação de responsabilidades, permitindo que empresas clientes gerenciem documentos, signatários e obtenham insights automáticos sobre seus contratos.

### Principais Funcionalidades

- ✅ **CRUD Completo**: Gerenciamento de Companies, Documents e Signers
- ✅ **Integração ZapSign**: Criação automática de documentos na API ZapSign
- ✅ **Análise com IA**: Análise inteligente de documentos com identificação de tópicos faltantes, resumo e insights
- ✅ **Webhooks**: Recebimento de eventos dos provedores de assinatura
- ✅ **Métricas e Alertas**: Dashboard com métricas agregadas e alertas automáticos
- ✅ **Documentação Swagger**: API completamente documentada com Swagger/OpenAPI
- ✅ **Autenticação por Token**: Sistema seguro de autenticação via tokens
- ✅ **Testes Automatizados**: Cobertura de testes com Pytest

## 🚀 Links de Produção

- **API em Produção**: https://zapsign-api.onrender.com
- **Documentação Swagger UI**: https://zapsign-api.onrender.com/api/schema/swagger-ui/
- **Documentação ReDoc**: https://zapsign-api.onrender.com/api/schema/redoc/
- **Schema OpenAPI**: https://zapsign-api.onrender.com/api/schema/
- **Painel Admin Django**: https://zapsign-api.onrender.com/admin/
- **Health Check**: https://zapsign-api.onrender.com/health/

## 🛠️ Tecnologias Utilizadas

### Backend
- **Django 5.0+**: Framework web Python
- **Django REST Framework 3.14+**: Construção de APIs REST
- **PostgreSQL**: Banco de dados relacional
- **drf-spectacular**: Geração automática de documentação OpenAPI/Swagger

### Integrações
- **ZapSign API**: Integração com provedor de assinatura digital
- **spaCy**: Processamento de linguagem natural para análise de documentos
- **Google Gemini API**: Análise avançada de conteúdo com IA generativa
- **PyPDF2 & pdfplumber**: Extração de texto de arquivos PDF

### Testes e Qualidade
- **Pytest**: Framework de testes
- **pytest-django**: Integração Pytest com Django
- **pytest-cov**: Cobertura de código
- **pytest-mock**: Mocking para testes

### Infraestrutura
- **Docker**: Containerização
- **Gunicorn**: Servidor WSGI para produção
- **Render**: Plataforma de deploy (produção)

## 📦 Configuração Local

### Pré-requisitos

- Docker e Docker Compose instalados
- Git

## 🐳 Configuração com Docker (Recomendado)

### 1. Clone o Repositório

```bash
git clone <repository-url>
cd zapsign_api
```

### 2. Configure Variáveis de Ambiente (Opcional)

Crie um arquivo `.env` na raiz do projeto para personalizar as configurações:

```bash
# Banco de Dados
POSTGRES_DB=zapsign_db
POSTGRES_USER=zapsign_user
POSTGRES_PASSWORD=zapsign_pass

# Django
SECRET_KEY=sua-chave-secreta-aqui
DEBUG=True

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:4200,http://localhost:3000

# Google Gemini (Opcional - para análise avançada)
GEMINI_API_KEY=sua-chave-gemini
GEMINI_ENABLED=True
GEMINI_MODEL=gemini-3-flash-preview

# ZapSign
ZAPSIGN_SANDBOX_URL=https://sandbox.api.zapsign.com.br
ZAPSIGN_PRODUCTION_URL=https://api.zapsign.com.br
```

> **Nota**: Se não criar o arquivo `.env`, o Docker Compose usará valores padrão.

### 3. Execute o Docker Compose

```bash
docker-compose up -d
```

Isso irá:
- Criar e iniciar o container do PostgreSQL
- Criar e iniciar o container do backend Django
- Aguardar o banco de dados ficar saudável antes de iniciar o backend

### 4. Execute as Migrações

```bash
docker-compose exec backend python manage.py migrate
```

### 5. Crie um Superusuário (Opcional)

```bash
docker-compose exec backend python manage.py createsuperuser
```

### 6. Instale o Modelo spaCy (Opcional, para análise de documentos)

Para análise de documentos com IA, instale o modelo spaCy:

```bash
# Modelo grande (recomendado - melhor qualidade)
docker-compose exec backend python -m spacy download pt_core_news_lg

# OU modelo pequeno (mais rápido, menor qualidade)
docker-compose exec backend python -m spacy download pt_core_news_sm
```

Após instalar, reinicie o container:

```bash
docker-compose restart backend
```

### 7. Acesse a API

A API estará disponível em: `http://localhost:8000`

- **Swagger UI**: http://localhost:8000/api/schema/swagger-ui/
- **ReDoc**: http://localhost:8000/api/schema/redoc/
- **Health Check**: http://localhost:8000/health/
- **Admin Django**: http://localhost:8000/admin/


## 🧪 Executando Testes

### Com Docker

```bash
# Executar todos os testes
docker-compose exec backend pytest

# Executar com cobertura
docker-compose exec backend pytest --cov=apps --cov-report=html

# Executar testes específicos
docker-compose exec backend pytest tests/test_views.py
```

## 🏗️ Arquitetura

O projeto segue os princípios de **Clean Architecture** com separação em camadas:

```
apps/
├── domain/          # Entidades e interfaces (camada de domínio)
│   ├── models/      # Modelos Django
│   └── interfaces/  # Interfaces/contratos
├── application/     # Casos de uso e lógica de negócio
│   ├── services/   # Serviços de aplicação
│   └── facades/     # Facades para integrações
├── infrastructure/  # Implementações concretas
│   ├── providers/  # Implementações de provedores
│   └── services/   # Serviços de infraestrutura
└── presentation/    # Camada de apresentação (API)
    ├── views/       # ViewSets e views
    ├── serializers/ # Serializers DRF
    └── urls/        # Rotas da API
```

## 🔐 Autenticação

A API utiliza autenticação por Token. Para obter um token:

```bash
POST /api/api-token-auth/
{
  "username": "seu_usuario",
  "password": "sua_senha"
}
```

Use o token retornado no header:

```
Authorization: Token <seu-token>
```

## 🔄 Fluxos da Aplicação

### Fluxo de Criação de Documento

```mermaid
flowchart TD
    Start([Usuário cria documento]) --> Form[Formulário com nome, URL PDF e signatários]
    Form --> Validate{Validação}
    Validate -->|"Inválido"| Error[Exibe erros]
    Validate -->|"Válido"| API[Envia para API ZapSign]
    API --> ZapSign[API ZapSign cria documento]
    ZapSign --> Response[Retorna token e open_id]
    Response --> Save[Salva no banco de dados]
    Save --> Success[Documento criado com sucesso]
    Error --> Form
```

### Fluxo de Análise de Documento com IA

Este fluxo mostra como a API analisa documentos usando Google Gemini com fallback automático para spaCy:

```mermaid
flowchart TD
    Start([Usuário solicita análise]) --> Extract[Extrai texto do PDF]
    Extract --> CheckGemini{Gemini configurado?}
    CheckGemini -->|"Não"| UseSpacy[Usa spaCy para análise]
    CheckGemini -->|"Sim"| TryGemini[Tenta analisar com Gemini]
    TryGemini --> GeminiSuccess{Sucesso?}
    GeminiSuccess -->|"Sim"| GeminiResult[Análise completa com Gemini]
    GeminiSuccess -->|"Erro de API"| Fallback1[Fallback para spaCy]
    GeminiSuccess -->|"Timeout"| Fallback2[Fallback para spaCy]
    GeminiSuccess -->|"Rate Limit"| Fallback3[Fallback para spaCy]
    Fallback1 --> UseSpacy
    Fallback2 --> UseSpacy
    Fallback3 --> UseSpacy
    UseSpacy --> SpacyResult[Análise completa com spaCy]
    GeminiResult --> Save[Salva análise no banco]
    SpacyResult --> Save
    Save --> Return[Retorna insights, resumo e tópicos faltantes]
```

### Fluxo Detalhado: Análise com Gemini e Fallback

```mermaid
sequenceDiagram
    participant User as Usuário
    participant API as API ZapSign
    participant Service as DocumentAnalysisService
    participant Gemini as Google Gemini
    participant Spacy as spaCy
    participant DB as Banco de Dados

    User->>API: POST /documents/:id/analyze
    API->>Service: analyze_document()
    Service->>Service: Extrai texto do PDF
    
    alt Gemini está configurado
        Service->>Gemini: Envia texto para análise
        alt Gemini responde com sucesso
            Gemini-->>Service: Insights, resumo, tópicos
            Service->>DB: Salva análise (provider: gemini)
            DB-->>Service: Análise salva
            Service-->>API: Retorna análise completa
        else Gemini falha (erro/timeout/rate limit)
            Gemini-->>Service: Erro
            Service->>Spacy: Fallback: analisa com spaCy
            Spacy-->>Service: Insights, resumo, tópicos
            Service->>DB: Salva análise (provider: spacy, fallback_reason)
            DB-->>Service: Análise salva
            Service-->>API: Retorna análise completa
        end
    else Gemini não configurado
        Service->>Spacy: Analisa diretamente com spaCy
        Spacy-->>Service: Insights, resumo, tópicos
        Service->>DB: Salva análise (provider: spacy)
        DB-->>Service: Análise salva
        Service-->>API: Retorna análise completa
    end
    
    API-->>User: Resposta com análise
```

### Fluxo de Envio para Assinatura

```mermaid
flowchart TD
    Start([Usuário envia documento para assinatura]) --> CheckStatus{Status do documento}
    CheckStatus -->|"Rascunho"| Validate{Validações}
    CheckStatus -->|"Outro status"| Error1[Erro: documento não está em rascunho]
    Validate -->|"Sem signatários"| Error2[Erro: adicione signatários]
    Validate -->|"Válido"| SendAPI[Envia para API ZapSign]
    SendAPI --> ZapSign[API ZapSign processa]
    ZapSign --> UpdateStatus[Atualiza status para 'pending']
    UpdateStatus --> Notify[Notifica signatários por email]
    Notify --> Success[Documento enviado com sucesso]
    Error1 --> End
    Error2 --> End
```

### Fluxo de Webhook

```mermaid
sequenceDiagram
    participant ZapSign as API ZapSign
    participant Webhook as Webhook Handler
    participant Facade as SignatureProviderFacade
    participant DB as Banco de Dados

    ZapSign->>Webhook: POST /webhooks/zapsign/
    Webhook->>Webhook: Extrai token do documento
    Webhook->>DB: Busca documento pelo token
    DB-->>Webhook: Documento encontrado
    Webhook->>Facade: process_webhook_event()
    Facade->>Facade: Processa evento (assinado, cancelado, etc.)
    Facade->>DB: Atualiza status do documento
    Facade->>DB: Atualiza status dos signatários
    DB-->>Facade: Atualização concluída
    Facade-->>Webhook: Processamento concluído
    Webhook-->>ZapSign: 200 OK
```

