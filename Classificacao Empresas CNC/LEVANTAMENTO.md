# Classificação de Empresas no Sistema Comércio — Levantamento e Decisões

> Documento de trabalho. Consolida o que temos, o que falta, decisões de negócio e
> pendências para automatizar a classificação de empresas quanto ao enquadramento no
> Sistema Comércio (plano da CNC).
>
> Status: **levantamento**. Nada implementado. Atualizado em 2026-09-03.

---

## 1. Objetivo

Dada a base de pessoas jurídicas (RFB / demais fontes do `empresa_hub`), classificar
automaticamente se cada empresa **faz parte do Sistema Comércio** — isto é, se a
atividade econômica que a define está enquadrada em um dos grupos do **plano da CNC**
no *Quadro de Atividades e Profissões* a que se refere o **art. 577 da CLT**.

O enquadramento determina, entre outros: contribuição ao SESC/SENAC, representação por
sindicatos filiados à CNC e o universo de "empresas do comércio" para arrecadação,
estudos econômicos e representação.

---

## 2. Decisões de negócio

### 2.1 Já definido

| # | Decisão | Origem |
|---|---|---|
| D1 | A regra normativa base é o **Quadro do art. 577 da CLT** + a **jurisprudência da CERSC** (Comissão de Enquadramento e Registro Sindical do Comércio). | Documentos entregues |
| D2 | A saída-alvo é binária no nível macro — **pertence / não pertence ao Sistema Comércio** — com detalhamento de categoria e grupo do plano. | Enunciado do projeto |
| D3 | As fontes de dados são as catalogadas no `empresa_hub` (MVP: RFB CNPJ Empresa/Estabelecimento/Sócios/Simples, RAIS Estabelecimento, Novo CAGED, CEIS). | `empresa_hub_mapeamento_fontes.xlsx` |
| D4 | Ambiente de execução: ecossistema **OráculoS / Microsoft Fabric** (mesma stack do pipeline RFB e do `empresa_hub`). | Contexto da Equipe de Dados |
| D5 | **Modo de uso: classificação em lote de toda a base** de PJ (não consulta caso a caso). | P1 |
| D6 | **Unidade de saída: empresa (CNPJ básico)**, avaliada a partir dos seus **estabelecimentos**. | P6 |
| D7 | **Preponderância aproximada pelo nº de vínculos da RAIS** por estabelecimento (proxy provisório). CNAE não serve como medida de peso/representatividade. | P4 |
| D8 | **"Indeterminado" é uma saída válida** no início do projeto. | P5 |
| D9 | Quadro do art. 577: usar o **PDF anotado** que temos, respeitando as marcações de grupo extinto. | P7 |
| D10 | Não existe de-para CNAE → plano pré-existente; o **crosswalk será construído** e homologado pela Divisão Jurídica. | P3 |
| D11 | `empresa_hub` é apenas a **organização/catálogo** de fontes já carregadas no Fabric — sem nova ingestão neste projeto. | P8 |

### 2.2 A decidir

- **Solução definitiva para preponderância** (faturamento/receita por atividade) — Gabriel investigando; RAIS vínculos é o proxy provisório.
- **Limiar de confiança** para automação sem revisão humana.
- Tratamento de **múltiplo enquadramento** na saída (além do "indeterminado").
- Rito de **homologação** da classificação pela Divisão Jurídica/Sindical antes de virar dado oficial.
- **Fallback** para estabelecimentos/empresas sem vínculo RAIS (ver Seção 7).

---

## 3. A regra de enquadramento (resumo normativo)

Base legal: CLT arts. 511, 570, 571, 572, 577, 580 e 581.

1. **O enquadramento é automático e decorre da atividade** — não é escolha da empresa (Proc. CERSC 1.195).
2. Vale a **atividade efetivamente exercida**, não o rol do contrato/estatuto social (Proc. 1.198, 1.093).
3. Identifica-se a **atividade preponderante** — "aquela para a qual convergem todas as demais, em regime de conexão funcional" (art. 581 §2º); apuração pelo **faturamento** (Proc. 1.405).
4. Enquadra-se a atividade em uma **categoria econômica do Quadro**: correspondência direta ou, na ausência de previsão expressa, por **similaridade / conexão** (art. 570, parágrafo único).
5. A categoria pertence a um **grupo** de uma **Confederação**. Se o grupo é da CNC → **é Sistema Comércio**.

**Regras especiais recorrentes na jurisprudência:**

- **Múltiplo / duplo enquadramento**: atividades autônomas sem preponderância → mais de um enquadramento, inclusive em planos distintos (comércio + indústria).
- **Indústria + venda da própria produção → indústria (CNI)**; só a revenda de produto de terceiro é comércio. Idem "produção seguida de distribuição" (energia, gás).
- **Serviços**: "serviço" não é categoria; serviços de natureza comercial caem, em regra, no **3º grupo** da CNC (agentes autônomos), com "assessoramento, perícias, informações e pesquisas" como categoria residual (holding, factoring, locação de veículos/máquinas, processamento de dados, franquia…).
- **Filial segue a matriz.**
- **Não são enquadráveis** (não exercem atividade econômica): cartório, condomínio, comissão de conciliação prévia, shopping center, associação sem capital social.
- **CNAE ≠ Quadro**: o CNAE do IBGE **não altera** o Quadro e "não esgota o rol"; o mesmo CNAE pode ser atacado ou varejo — grupos distintos (Proc. 1.136, 1.141).
- Sem fins lucrativos / cooperativa: enquadra-se pelo **setor econômico**, independe de lucro.

Plano da CNC (6 grupos): ver **Anexo A**.

### 3.1 Como vamos operacionalizar (v0)

Sem objeto social e sem faturamento, a regra é aproximada assim:

1. **Grão de análise: estabelecimento ativo** (RFB Estabelecimento). Para cada um, o **CNAE fiscal principal** → categoria / grupo / plano pelo crosswalk (Seção 5.3). CNAEs secundários entram só como sinal de múltiplo/ambiguidade nesta versão.
2. **Peso do estabelecimento = nº de vínculos ativos na RAIS** (último ano disponível). Estabelecimento sem vínculos → peso 0, registro mantido para fallback.
3. **Agregação para a empresa (CNPJ básico)**, ponderando os estabelecimentos pelo peso:
   - peso majoritário em grupos da **CNC** → **pertence ao Sistema Comércio**;
   - peso majoritário **fora da CNC** → **não pertence**;
   - sem maioria clara, CNAE ambíguo (Anexo B) ou nenhum estabelecimento com vínculos → **indeterminado**.
4. **Regras especiais por cima**: não-enquadráveis (natureza jurídica / CNAE de cartório, condomínio, administração pública…), indústria + revenda, filial segue matriz.
5. **Saída por empresa**: `pertence_sistema_comercio ∈ {sim, não, indeterminado}`, `grupo(s)`, `plano(s)`, `peso_cnc_%`, `criterio`, `confianca`, `flags` (múltiplo, ambíguo, sem_vínculos, indústria_comércio…).

---

## 4. O que temos hoje

### 4.1 Documentos normativos (nesta pasta)

| Arquivo | Conteúdo | Formato / limitação |
|---|---|---|
| `Quadro de Atividades do art. 577 CLT.pdf` (16 p.) | Taxonomia oficial: Confederação → grupo → categoria econômica (+ categoria profissional). Plano da CNC destacado. | **PDF, tabelas não estruturadas**; versão anotada (marca grupos "extintos"); falta confirmar consolidação vigente. |
| `Indexação (Pareceres CERSC).doc` | **124 pareceres** (linhas "Processo nº") agrupados em **~100 verbetes temáticos** em ordem alfabética. Ementas de decisões da CERSC (CNC / Divisão Jurídica e Sindical, 2024), com nº do processo, data e o enquadramento decidido. Cada parecer cita **uma empresa real**. | **Só a ementa**, não o inteiro teor; casos de **~1995 a 2007** (maioria 2002–2007); base pequena. Dos ~100 verbetes, **~80 tratam de "atividade → enquadramento"** (úteis para o crosswalk e a validação) e **~20 são temas sindicais/processuais** (conflito de representação, dissociação, criação de sindicato, contribuição) — úteis só para a doutrina. |

### 4.2 Dados — catálogo `empresa_hub` (`empresa_hub_mapeamento_fontes.xlsx`)

15 fontes mapeadas; **7 no MVP**:

| Fonte | Órgão | Grão | Periodic. | Relevância para classificação |
|---|---|---|---|---|
| CNPJ – Empresa | RFB | CNPJ básico | Mensal | Razão social, natureza jurídica, **porte**, capital social, ente federativo |
| CNPJ – Estabelecimento | RFB | CNPJ 14 díg. | Mensal | **CNAE fiscal principal + secundárias**, matriz/filial, situação cadastral, início de atividade, UF/município |
| CNPJ – Sócios | RFB | sócio × empresa | Mensal | Composição societária (uso marginal para enquadramento) |
| CNPJ – Simples Nacional | RFB | CNPJ básico | Mensal | Opção Simples/MEI (sinal de porte/regime) |
| RAIS – Estabelecimento | MTE | CNPJ 14 díg. | Anual | **Qtd. vínculos ativos por estabelecimento** (proxy de peso da atividade), CNAE 2.0 classe/subclasse, natureza jurídica, porte, Simples |
| Novo CAGED – Movimentação | MTE | movimentação | Mensal | **Sem CNPJ individual** — só agregados por seção/subclasse CNAE. Serve para validação macro, não para classificar empresa. |
| CEIS – Sanções | CGU | sanção × CNPJ | Mensal | Sem relação com enquadramento. Fora do escopo deste módulo. |

Fontes **futuras** relevantes: Arrecadação RFB (macro, tributo × UF × CNAE), Comex Stat (exportadores por CNPJ × NCM), Parcelamentos.

### 4.3 Tabelas de domínio / referência (nos arquivos de layout RAIS)

- **CNAE 2.0**: seção (21), divisão (~87), classe (~670), subclasse (~1.331) — com descrições.
- **CNAE 1.0 / CNAE 95**: classes — para ponte entre versões (pareceres antigos usam CNAE anterior).
- Município (IBGE), UF, CBO (ocupação 94 e 2002).

### 4.4 Infraestrutura já existente

- **Pipeline RFB no Fabric** (projeto irmão `rfb - fabric`): ingestão mensal dos 10 datasets do CNPJ, camadas Bronze/Silver/Gold com dimensões SCD2 (`gold.rfb_dim_empresa`, `rfb_dim_estabelecimento`, `rfb_dim_socio`) e fato mensal. **A entrada cadastral já está pronta e versionada no tempo.**
- Projeto `empresa_hub` como camada de integração das fontes acima.

---

## 5. O que está faltando

### 5.1 Base de conhecimento da regra

- [ ] **Quadro do art. 577 estruturado** (Confederação → grupo → categoria), com marcação do que é/não é CNC e das categorias extintas. Hoje só em PDF.
- [ ] **Pareceres CERSC estruturados** — 1 registro por caso: atividade analisada, categoria de enquadramento, grupo/plano, critério aplicado (preponderância / similaridade / conexão / múltiplo / não-enquadrável), nº do processo.
- [ ] **Inteiro teor dos pareceres** (a ementa não basta para o raciocínio de similaridade) e pareceres **pós-2007**, se existirem.
- [ ] Texto dos artigos da CLT usados como critério.

### 5.2 Dados de entrada

- [x] **Preponderância** → aproximada pelo **nº de vínculos RAIS** por estabelecimento (D7). Solução de faturamento por atividade fica como melhoria futura.
- [ ] **Objeto social** (contrato/estatuto) — a RFB não fornece; assumido **fora de escopo na v0**. Reavaliar se a taxa de "indeterminado" ficar alta.
- [ ] **Cobertura RAIS**: dimensionar quantos estabelecimentos/empresas ativos **não** têm vínculo declarado (provável maioria) e definir o fallback.
- [ ] Sinais para regras especiais: indústria que também revende, cooperativa, entidade sem capital social — o que dá para inferir de **natureza jurídica + CNAE**.

### 5.3 Crosswalk CNAE 2.0 → Quadro do art. 577 — **peça central**

Confirmado que **não existe** de-para pré-existente (P3): será construído neste projeto e homologado pela Divisão Jurídica.

- [ ] Tabela de-para das **~1.331 subclasses CNAE 2.0** para: `{Confederação, grupo do plano, categoria econômica do Quadro, critério (direto/similaridade/conexão), fonte (parecer nº / interpretação), flag de ambiguidade}`.
- [ ] Marcar CNAEs **ambíguos** que dependem de análise casuística (atacado × varejo, indústria × comércio, serviço, produção × distribuição).
- [ ] Primeira versão a partir do **Anexo B**, refinada subclasse a subclasse; cruzar com os ~80 verbetes CERSC de atividade para os casos já decididos.
- [ ] Definir dono e rito de **homologação/manutenção** do crosswalk (Divisão Jurídica/Sindical).

### 5.4 Motor de decisão

- [ ] Camada **determinística** (cobre a maior parte da base): CNAE(s) → crosswalk → é CNC?
- [ ] Camada de **raciocínio** para os casos sem correspondência direta: similaridade/conexão contra Quadro + pareceres — candidato a **RAG + LLM** (stack do `Research Paper Assistant` / `Módulo IA - Oráculo`).
- [ ] Regras explícitas: múltiplo enquadramento, indústria+comércio, serviços → 3º grupo, não-enquadráveis, filial segue matriz.
- [ ] Esquema de saída: `pertence_sistema_comercio` (sim/não/parcial/indeterminado), `categoria(s)`, `grupo(s)`, `criterio_aplicado`, `pareceres_citados`, `confianca`, `requer_revisao_humana`.

### 5.5 Validação

- [ ] **Conjunto rotulado**: cada parecer CERSC cita uma empresa real e a decisão → **124 casos "ouro"** a extrair (empresa + atividade + enquadramento).
- [ ] Amostra da base classificada e revisada manualmente pela Divisão Jurídica/Sindical.
- [ ] Métricas por classe e por grupo; foco em falso-positivo/negativo de "é comércio".
- [ ] Reconciliação macro contra CAGED/RAIS por seção CNAE (nº de empresas e vínculos do comércio).

---

## 6. Pendências / perguntas em aberto

### 6.1 Resolvidas nesta rodada

| # | Pergunta | Resposta |
|---|---|---|
| P1 | Uso final | **Classificar a base toda** (lote). |
| P2 | Inteiro teor dos pareceres / base histórica / CERSC pós-2007 | Provavelmente conseguimos — a confirmar/obter. |
| P3 | De-para CNAE → plano já existe? | **Não.** Construir o crosswalk (Seção 5.3). |
| P4 | Proxy de preponderância | **Nº de vínculos RAIS** por enquanto; busca-se solução de faturamento por atividade. |
| P5 | "Indeterminado" na saída | **Sim, aceito** no início do projeto. |
| P6 | Unidade de análise | **Empresa (CNPJ básico), avaliada pelos estabelecimentos.** |
| P7 | Versão do Quadro | Usar o **PDF anotado** que temos. |
| P8 | `empresa_hub` ingere dados? | Não — é só **organização do que já está carregado** no Fabric. |

### 6.2 Ainda em aberto

- **P2** — obter o inteiro teor dos pareceres CERSC e eventual base histórica de enquadramentos.
- **P4′** — solução definitiva para faturamento/receita por atividade (Gabriel investigando).
- **Fallback** para estabelecimentos/empresas sem vínculo RAIS.
- **Limiar de confiança** para dispensar revisão humana.
- Rito de **homologação jurídica** da saída antes de virar dado oficial.

---

## 7. Riscos e limitações conhecidas

- **CNAE pode estar desatualizado ou incorreto** no cadastro da RFB — e é a nossa principal (às vezes única) evidência da atividade. A doutrina manda olhar a atividade *real*, que não temos.
- **Sem faturamento**, a preponderância (art. 581 §2º) é aproximada, não apurada. Todo múltiplo enquadramento fica sujeito a erro.
- **CNAE ≠ Quadro** por princípio — o crosswalk é interpretação, não norma; precisa de homologação jurídica e vira ponto de contestação.
- **RAIS**: anual, defasada, em transição para o eSocial, e não cobre empresas sem empregados / boa parte dos MEIs.
- **A ponderação por vínculos RAIS só cobre empresas com empregados declarados** — provavelmente a minoria dos CNPJs ativos. Para o restante, a decisão cai no CNAE principal puro (menor confiança) ou em "indeterminado". Dimensionar isso é prioridade.
- Dentro de **um mesmo estabelecimento** os CNAEs secundários seguem sem peso — a RAIS traz só um CNAE por estabelecimento. O desempate por vínculos só funciona *entre* estabelecimentos.
- Base de pareceres pequena e antiga → cobertura limitada de atividades novas (tecnologia, plataformas, economia digital).
- Categorias por **similaridade/conexão** são decisões humanas registradas caso a caso; o modelo vai *imitar*, não *deduzir* — exige revisão.

---

## 8. Próximos passos sugeridos

1. Estruturar o **Quadro do art. 577** em tabela (esforço baixo, destrava tudo).
2. Estruturar os **124 pareceres CERSC** em tabela (tema · processo · data · atividade analisada · categoria/grupo/plano · critério · empresa citada) + extrair o conjunto rotulado.
3. Obter inteiro teor dos pareceres / base histórica (P2).
4. Montar **crosswalk CNAE 2.0 → Quadro** — v1 a partir do Anexo B, refinada por subclasse, cruzada com as ementas.
5. **Dimensionar a cobertura RAIS** na base ativa (quantos CNPJs têm vínculo) — define o peso real do fallback.
6. Protótipo do **motor v0 (Seção 3.1)** sobre uma amostra da base; medir % pertence / não / indeterminado e a zona cinzenta.

---

## Anexo A — Plano da CNC (Quadro do art. 577)

| Grupo | Nome | Exemplos de categorias econômicas |
|---|---|---|
| 1º | Comércio Atacadista | "comércio atacadista de …" (gêneros alimentícios, material de construção, drogas e medicamentos, maquinismos, papel e papelão, sucata, minérios…) |
| 2º | Comércio Varejista | lojistas do comércio; "comércio varejista de …"; estabelecimentos de serviços funerários |
| 3º | Agentes Autônomos do Comércio | representantes comerciais, corretores, leasing, administradoras de consórcio, **assessoramento/perícias/informações e pesquisas**, processamento de dados, segurança e vigilância, serviços contábeis, auto e moto escolas, locação de fitas/vídeos |
| 4º | Comércio Armazenador | armazéns gerais, entrepostos, trapiches, comissários/consignatários e comércio de café (exceto varejo) |
| 5º | Turismo e Hospitalidade | hotéis/bares/restaurantes e similares, empresas de turismo, casas de diversões, barbeiros/cabeleireiros/institutos de beleza, **compra, venda, locação e administração de imóveis**, asseio e conservação, lavanderias, instituições beneficentes/religiosas/filantrópicas, conservação de elevadores, empresas exibidoras cinematográficas |
| 6º | Estabelecimentos de Serviços de Saúde | hospitais, clínicas, casas de saúde, laboratórios de análises, bancos de sangue, cooperativas de serviços médicos, empresas de medicina de grupo, prótese dentária |

---

## Anexo B — Mapa preliminar CNAE 2.0 (seção) → plano

> **Primeira aproximação, a validar subclasse a subclasse com a Divisão Jurídica.**
> "Ambíguo" = a seção mistura atividades de planos diferentes e exige regra fina.

| Seção CNAE 2.0 | Descrição | Enquadramento provável | Comércio? |
|---|---|---|---|
| A | Agricultura, pecuária, produção florestal, pesca | Plano rural (fora da CNC) | Não |
| B | Indústrias extrativas | CNI – 5º grupo (extrativas) | Não |
| C | Indústrias de transformação | CNI | Não (salvo revenda de terceiros → duplo) |
| D | Eletricidade e gás | CNI se produz; CNC 3º grupo se só distribui | **Ambíguo** |
| E | Água, esgoto, resíduos | CNI – 4º grupo (indústrias urbanas) | Não (pareceres: tratamento de água) |
| F | Construção | CNI – 3º grupo (construção e mobiliário) | Não |
| G | Comércio; reparação de veículos e motos | **CNC** – 1º grupo (div. 46, atacado), 2º grupo (div. 45 e 47, varejo) | **Sim** (reparação pode ser serviço/indústria) |
| H | Transporte, armazenagem e correio | CNT (transporte); **exceto** armazenagem (div. 52) → CNC 4º grupo, agenciamento de carga → CNC 3º | **Ambíguo** |
| I | Alojamento e alimentação | **CNC** – 5º grupo (turismo e hospitalidade) | **Sim** |
| J | Informação e comunicação | Telecom/rádio/TV → CN Comunicações; TI/software/portais/tratamento de dados → CNC 3º grupo; edição de livros → CN Educação e Cultura | **Ambíguo** |
| K | Atividades financeiras e seguros | CN Empresas de Crédito; **exceto** factoring, promotoras, holdings, corretagem → CNC 3º grupo (pareceres) | **Ambíguo** |
| L | Atividades imobiliárias | **CNC** – 5º grupo (compra, venda, locação e administração de imóveis) | **Sim** |
| M | Atividades profissionais, científicas e técnicas | **CNC** – 3º grupo (assessoramento, perícias, informações e pesquisas), em regra; profissões liberais reguladas têm plano próprio | **Sim** (com exceções) |
| N | Atividades administrativas e serviços complementares | **CNC** – 3º grupo (locação de máquinas/veículos, segurança e vigilância) e 5º grupo (asseio e conservação, agências de viagem) | **Sim**, em regra |
| O | Administração pública | Não enquadrável | Não |
| P | Educação | CN Educação e Cultura | Não |
| Q | Saúde humana e serviços sociais | **CNC** – 6º grupo (estab. de serviços de saúde); serviços sociais/assistência → CN Educação e Cultura ou 5º grupo (instituições beneficentes) | **Ambíguo** (saúde = sim) |
| R | Artes, cultura, esporte e recreação | CN Educação e Cultura (cultura física, diversões); **exceto** casas de diversões / diversões eletrônicas → CNC 5º grupo (pareceres) | **Ambíguo** |
| S | Outras atividades de serviços | Reparação → indústria; lavanderias, cabeleireiros, atividades de associações → CNC 5º grupo | **Ambíguo** |
| T | Serviços domésticos | Não enquadrável | Não |
| U | Organismos internacionais | Não enquadrável | Não |
