# Mytrip

MyTrip é uma aplicação em Flask para gerenciar viagens e suas atividades, 
com foco principal em controle de orçamento. 

## 🏗️ Arquitetura e Pipeline de Deploy (CI/CD)

Este projeto esta sendo desenvolvido com foco em implementar boas práticas de engenharia de software.

O objetivo desta documentação é explicar, de forma clara e técnica, como a aplicação é construída, versionada e disponibilizada em produção, servindo tanto como material de estudo quanto como referência profissional.

## 📌 Visão Geral da Arquitetura

#### A aplicação é composta por dois serviços independentes:

* Frontend: responsável pela interface com o usuário

* Backend: responsável pela API e regras de negócio

#### Cada serviço é:

* empacotado em um container Docker

* versionado como uma imagem Docker

* executado de forma independente no Google Cloud Run

Essa separação permite escalabilidade independente, melhor organização e menor acoplamento entre as camadas do sistema.

## ☁️ Arquitetura em Produção (Cloud Run)

* Cada serviço (frontend e backend) é um Cloud Run Service distinto

* O Cloud Run executa containers a partir de imagens Docker

* A cada deploy, uma nova revisão (revision) é criada

* O tráfego é migrado automaticamente entre revisões, garantindo zero downtime

O frontend se comunica com o backend via requisições HTTP para a API, utilizando a URL do backend configurada por variáveis de ambiente.

## 🐳 Docker e Containerização
### Dockerfile

Cada serviço possui seu próprio Dockerfile, que descreve:

* a imagem base

* as dependências

* o código da aplicação

* o comando de inicialização

O Dockerfile define como a aplicação deve ser construída, mas não executa nada por si só.

### Imagem Docker

A imagem Docker é o artefato executável imutável gerado a partir do Dockerfile. Ela contém tudo o que a aplicação precisa para rodar de forma idêntica em qualquer ambiente.

## 📦 Artifact Registry

As imagens Docker geradas no processo de build são armazenadas no Artifact Registry (GCP).

Ele funciona como o ponto de transição entre:

* CI (construção da imagem)

* CD (execução da imagem em produção)

O Cloud Run sempre consome imagens a partir do Artifact Registry.

## ⚙️ CI/CD com GitHub Actions

O projeto utiliza GitHub Actions para automatizar todo o fluxo de build e deploy.

### Workflow

Os workflows ficam localizados em:

`.github/workflows/`

O projeto utiliza um único workflow, responsável por orquestrar o build e deploy do frontend e do backend.

Esse workflow define:

* quando a automação deve rodar (trigger)

* em qual ambiente (VM temporária)

* quais etapas devem ser executadas para cada serviço

### Trigger

Os workflows são disparados automaticamente a partir de eventos como:

* push na branch principal (main)

* alterações em pastas específicas (frontend/ ou backend/)

Isso evita rebuilds e deploys desnecessários.

## 🔁 Fluxo Completo de Deploy

O fluxo de deploy segue a seguinte sequência lógica:

1. Uma alteração de código é enviada ao repositório

2. O evento dispara um workflow do GitHub Actions

3. Uma máquina virtual temporária é criada

4. O código é clonado

5. A imagem Docker é construída (build)

6. A imagem é enviada ao Artifact Registry

7. O Cloud Run cria uma nova revisão do serviço

8. O tráfego é migrado para a nova revisão (zero downtime)

Todo esse processo é automatizado, reprodutível e seguro.

## 🔐 Separação de Responsabilidades

* Dockerfile: descreve como empacotar a aplicação

* Workflow: descreve quando e como automatizar build e deploy

* Cloud Run: executa containers

Essa separação garante um sistema desacoplado, manutenível e profissional.