# Relatório de procedimento — pipeline cinemática do dataset *karate stances*

**Data de geração**: 2026-05-15
**Autor**: Pavani (com pipeline implementada em Python)
**Item Figshare**: [10.6084/m9.figshare.32288943](https://doi.org/10.6084/m9.figshare.32288943)
**Código aberto**: <https://github.com/luiz-pavani/karate-stances-dataset-scripts>

Este documento descreve, passo a passo, como os dados cinemáticos brutos exportados pelo Theia3D foram transformados nos três CSVs de análise (`kinematic_analysis_wide.csv`, `kinematic_analysis_long.csv`, `kinematic_analysis_codebook.csv`). Serve como referência metodológica para revisão, reprodutibilidade e descrição no Cap 2 da dissertação.

---

## 1. Dados de entrada

### 1.1 Acervo bruto

- **Localização**: `/Users/judo365/Documents/MASTER ESPORTES/MESTRADO/Artigos/DATASET/Kinematic Data/`
- **Tamanho**: 1,3 GB · 765 arquivos
- **Estrutura**:
  ```
  Kinematic Data/
  ├── ID003 ... ID014               12 sujeitos
  │   ├── <ZEN|KOK|KIB>/T<1..5>/    base × trial
  │   │   ├── *_pose_0.c3d          Theia3D output bruto
  │   │   ├── *_pose_filt_0.c3d     Theia3D filtrado 20 Hz (uso padrão)
  │   │   ├── *_Theia.trc           markers em formato .trc
  │   │   ├── Visual3d_SIMM_*.mot   placeholders vazios
  │   └── STATIC/T1/                referência anatômica (ID006-ID014)
  └── Pipelines/                    scripts Visual3D para export landmarks
  ```
- **Inventário total**: 189 trials (180 dinâmicos + 9 STATIC)
- **Aquisição**: Laboratório de Biomecânica do Porto (LABIOMEP), 8-câmera Qualisys Oqus + 2× Bertec FP4060-15
- **Software de reconstrução**: Theia3D v2024.1.24 (markerless)
- **Frequência de amostragem**: 180 Hz
- **Duração por trial**: 9,00 s exatos (1620 frames)

### 1.2 Auditoria preliminar (antes de processar)

Antes de escrever qualquer linha de código produtiva, fiz uma inventariação completa:

```bash
find "$DIR" -type f | sed 's/.*\.//' | sort | uniq -c
#   573 c3d
#   180 txt   (exports Visual3D POS+COM)
#     4 v3s   (scripts Visual3D)
#     2 mot   (placeholders SIMM)
#     1 trc, 1 cmz, 1 cmx
```

**Anomalias detectadas e tratadas**:

1. **Typo de aquisição**: pasta `ID009/KUK/` deveria ser `KOK` — typo do operador. Resolvi no loader (`BASE_CANONICAL = {"KUK": "KOK"}`) sem renomear arquivos originais (preservação da fonte).
2. **STATIC ausente** para ID003, ID004, ID005 — coleta piloto sem static reference; tratados com normalização pelo primeiro segundo do trial.
3. **Pastas `ALL_TRIALS` e `ALL_TRIALS_BASES`** com cópias dos `_pose_filt_0.c3d` — ignoradas no `discover_trials()` para evitar duplicação.

### 1.3 Inspeção do formato C3D

Confirmei via `ezc3d` que cada C3D contém:
- `data.rotations`: shape `(4, 4, 19, 1620)` — 19 segmentos × matriz 4×4 × 1620 frames
- `data.points`: vazio (sem markers tradicionais — Theia é markerless)
- `data.analogs`: vazio (kinetics em arquivo separado)
- **Parâmetros THEIA3D**: inertia params gender-specific por segmento (mass%, COM no frame do segmento, raios de giração)

Os 19 segmentos são:
```
worldbody, pelvis, l_thigh, l_shank, l_foot, l_toes,
r_thigh, r_shank, r_foot, r_toes,
head, torso,
l_uarm, l_larm, l_hand, r_uarm, r_larm, r_hand,
pelvis_shifted
```

---

## 2. Ambiente computacional

### 2.1 Stack escolhida

| Componente | Versão | Justificativa |
|---|---|---|
| **Python** | 3.13.2 | open-source; replicável por qualquer revisor sem licença MATLAB |
| **ezc3d** | 1.7.0 | leitor C3D oficial (Wagnon Sangeux/Inria); equivalência total com MATLAB BTK |
| **numpy** | 2.4.1 | álgebra linear |
| **scipy** | 1.17.1 | Butterworth + `Rotation` para decomposição Euler |
| **pandas** | 3.0.0 | DataFrames + CSV I/O |
| **matplotlib** | 3.10.9 | figuras diagnósticas |

### 2.2 Decisão sobre input

Optei por usar **`_pose_filt_0.c3d`** como input padrão (Theia já filtrou 20 Hz Butterworth zero-lag, validado em Kanko et al. 2021a,b). Os arquivos `_pose_0.c3d` (raw) também são incluídos no release Figshare para usuários que queiram re-filtrar com seus próprios parâmetros.

---

## 3. Arquitetura da pipeline

A pipeline foi desenhada em 8 módulos com responsabilidades isoladas, sob `karate-stances-dataset-scripts/src/python/kds/`:

```
kds/
├── loader.py             ─ leitura C3D + Visual3D POS + alias KUK→KOK + descoberta
├── demographics.py       ─ tabela canônica dos 12 sujeitos
├── kinematics_linear.py  ─ joint centres + COM whole-body + velocidades + acelerações
├── kinematics_angular.py ─ 12 ângulos articulares ISB
├── strike_detection.py   ─ auto-detecção gyaku-tsuki via hand speed
├── descriptors.py        ─ painel de descritores por janela
├── batch.py              ─ CLI driver para rodar nos 189 trials
└── plots.py              ─ figuras diagnósticas
```

---

## 4. Procedimento de processamento — passo a passo

### Passo 1 — Loader (`loader.py`)

**Entrada**: caminho para C3D.
**Saída**: `TrialRecord` (dataclass) contendo:
- `subject`, `base`, `trial`, `filtered`
- `rate_hz`, `n_frames`, `time` (array temporal)
- `segments`: dict `{label: (4, 4, n_frames)}` — 19 transforms 4×4 ao longo do tempo
- `inertia`: parâmetros inerciais gender-specific por segmento
- `metadata`: versão Theia, modelo, filtros, paths

**Validação**:
- Filename regex valida nomenclatura
- `BASE_CANONICAL = {"KUK": "KOK"}` resolve typo silenciosamente
- Cross-check: `rate_hz=180.0` e `n_frames=1620` confirmados em todos os 180 dynamic trials

### Passo 2 — Cinemática linear (`kinematics_linear.py`)

**2.1 Joint centres (posição da origem de cada segmento)**
Para cada segmento, a posição da origem no frame do laboratório é simplesmente a coluna 4 (translação) da matriz 4×4 homogênea:
```
T_segment = [ R  t ]   →  position_lab = T[0:3, 3, :]
            [ 0  1 ]
```

**2.2 Centro de massa whole-body**
Fórmula:
```
COM_lab(t) = Σ_i m_i × (R_i(t) × COM_local_i + t_i(t))
                                                          / Σ_i m_i
```
onde:
- `m_i` = massa percentual do segmento `i` (Theia stored, gender-specific)
- `COM_local_i` = posição do COM no frame do segmento (Theia stored)
- `R_i(t), t_i(t)` = rotação + translação do segmento no laboratório no frame `t`

Implementado em `whole_body_com()` via einsum vetorizado. Usei **sex-specific** (`sex='M'` ou `'F'` da demografia).

**Pelvis e pelvis_shifted** não têm inertia params no Theia (a massa do tronco-baixo está distribuída entre thorax e thighs no modelo Theia) — excluídos do somatório.

**2.3 Velocidades e acelerações**
- Velocidade: `np.gradient(position, 1/rate, axis=-1)` — diferenças centrais
- Aceleração: pré-filtragem **6 Hz Butterworth 4ª ordem zero-lag** + dupla derivação (suprime ruído amplificado pela segunda derivada)

### Passo 3 — Cinemática angular (`kinematics_angular.py`)

**3.1 Definições articulares (12 joints × 3 axes = 36 DoF)**

Sigo recomendações ISB (Wu et al. 2002 lower limb + spine; Wu et al. 2005 upper limb):

| Joint | Parent | Child | Sequência Euler |
|---|---|---|---|
| hip_right/left | pelvis | thigh | Z-X-Y |
| knee_right/left | thigh | shank | Z-X-Y |
| ankle_right/left | shank | foot | Z-X-Y |
| shoulder_right/left | torso | uarm | Y-X-Z |
| elbow_right/left | uarm | larm | Y-X-Z |
| pelvis_world | worldbody | pelvis | Z-X-Y |
| trunk | pelvis | torso | Z-X-Y |

**3.2 Decomposição**
```python
R_rel = R_parent.T @ R_child         # rotação relativa
angles = Rotation.from_matrix(R_rel).as_euler(seq, degrees=True)
```

Os 3 ângulos correspondem a: **flexão/extensão** (axis 0), **abdução/adução** (axis 1), **rotação interna/externa** (axis 2).

**3.3 ROM**
Para cada janela (pre/post-strike), `ROM = max − min` por axis. Cotovelo em movimento dinâmico pode ter gimbal lock (ROM 360°) — limitação conhecida do Euler; janelas estáticas (pre/post) não sofrem desse problema.

### Passo 4 — Strike detection (`strike_detection.py`)

**Algoritmo**:
1. Computa velocidade escalar (módulo) de `r_hand` e `l_hand` (origens das mãos)
2. Seleciona automaticamente o lado com maior peak speed
3. Marca:
   - `peak_time`: tempo do máximo
   - `peak_speed`: módulo no máximo
   - `onset_time`: primeiro cruzamento ascendente de 10% do peak antes do peak
   - `return_time`: primeiro cruzamento descendente de 10% do peak após o peak

**Validação descritiva (180 trials)**:
- Peak time: 4,02 ± 0,21 s (≈ 1 s após "*vai*" nominal aos 3 s — coerente com reação + execução)
- Peak speed: 5,99 ± 0,74 m/s (range literário 5–9 m/s para tsuki elite/sub-elite)

### Passo 5 — Descritores (`descriptors.py`)

**Janelas de análise**:
- `pre_strike = [1,0, 3,0] s` → 360 frames (postura assumida, antes do "vai")
- `post_strike = [6,0, 9,0] s` → 540 frames (postura re-estabilizada após strike)
- Janela de strike `[3,0, 6,0] s` preservada no time-series mas excluída dos summary descriptors

**Painel de descritores por janela (50+ scalars)**:

*COM (9 cols por janela)*:
- `com_x/y/z_mean_m`
- `com_ml/ap/z_range_cm`
- `com_ml/ap_rms_cm`
- `com_path_length_cm` (2D ML+AP)

*Joint angles (24 cols por janela = 12 joints × 2 stats)*:
- `<joint>_<flx|abd|rot>_mean_deg`
- `<joint>_<flx|abd|rot>_rom_deg`

*BoS (5 cols, só pré-strike pois pés estão fixos)*:
- `bos_width_ml_cm`
- `bos_depth_ap_cm`
- `bos_area_cm2` (bounding box dos 6 landmarks dos pés)
- `bos_centroid_x/y`

*Strike event (5 cols)*:
- `strike_hand`, `strike_peak_speed_mps`, `strike_peak_time_s`, `strike_onset_time_s`, `strike_return_time_s`

*Cross-pipeline validation (1 col)*:
- `v3d_com_offset_norm_mm` — distância média entre COM-Theia (nosso) e COM-Dempster (Visual3D export). Esperado: ~10-20 mm (diferença entre modelos inerciais).

### Passo 6 — Batch driver (`batch.py`)

**Comando**:
```bash
python -m kds.batch \
  --data-root "/Users/.../Kinematic Data" \
  --output-dir ./output
```

**Procedimento**:
1. `discover_trials()` retorna 189 paths (180 dynamic + 9 STATIC)
2. `discover_pos_txt()` mapeia 180 POS exports
3. Para cada trial:
   a. `read_c3d_trial()` carrega
   b. Para STATIC: COM mean sobre toda a duração
   c. Para dynamic: `trial_descriptors()` computa painel completo
4. Emite 5 outputs:
   - `summary_all_trials.csv` (180 rows × 181 cols)
   - `summary_static.csv` (9 rows × 12 cols)
   - `subject_means.csv` (36 rows — média por subject × base)
   - `qc_report.csv` (189 rows — flags QC)
   - `pipeline_metadata.json` (versão pipeline + timestamp)

**Tempo de execução**: ~70 segundos para os 189 trials no MacBook.

**Resultado**: 189/189 trials processados sem erro.

### Passo 7 — Consolidação para análise (`build_analysis_csv.py`)

A partir de `summary_all_trials.csv`, esta etapa final faz o join com a demografia e gera os 3 CSVs de análise:

**7.1 Wide (`kinematic_analysis_wide.csv`, 180 × 200)**
- Reordena colunas: identificadores → demografia → descritores
- Adiciona 5 normalizações por altura (úteis para comparações cross-subject):
  - `com_height_norm_by_height` = `pre_com_z_mean_m / (height_cm/100)`
  - `bos_area_norm_by_height_sq_pct` = `bos_area_cm2 / height_cm² × 100`
  - `bos_width_norm_by_height_pct`, `bos_depth_norm_by_height_pct`
  - `strike_peak_speed_norm_by_height_sqrt`

**7.2 Long (`kinematic_analysis_long.csv`, 31.860 × 22)**
- Melt do wide: uma linha por (trial, métrica)
- Cada linha carrega id_vars (subject, base, sex, style, etc.) + (metric, value)
- Auto-anotação: cada métrica é parseada em `window`, `family`, `joint`, `axis`, `stat`, `unit` para facilitar filtragem em R/Python
- Formato pronto para `lmer()` em R ou `mixedlm()` em statsmodels

**7.3 Codebook (`kinematic_analysis_codebook.csv`, 200 × 3)**
- Uma linha por coluna do wide
- Campos: `column`, `description`, `dtype`
- Descrições construídas via lookup table (identificadores/demografia) e família de prefixo (`pre_com_`, `post_hip_`, etc.)

---

## 5. Validação e QC

### 5.1 Trial completeness
- 180/180 dynamic trials processados ✅
- 9/9 STATIC processados ✅
- 0 erros ✅

### 5.2 Cross-pipeline validation
COM computado por mim (Theia inertia gender-specific) vs COM exportado pelo Visual3D (Dempster inertia):
- Mean offset: **12,1 ± 5,2 mm** (n=180)
- Esperado da literatura: 10–20 mm entre modelos inerciais diferentes ✅

### 5.3 Strike detection plausibility
- Peak time: 4,02 ± 0,21 s
- "*Vai*" nominal: 3,00 s
- Latência reação+execução: ≈1 s — coerente com tempos de reação tsuki (Pozo 2011, Cesari 2008)

### 5.4 Sanity check biomecânico
Tabela `BoS depth (cm) × base × style`:
```
style       Goju-Ryu  Shotokan  Wado-Ryu
base
KIB           102.1      96.8      82.4
KOK            53.0      92.0      80.1   ← contraste-bomba
ZEN            88.6      86.1      73.5
```

KOK Goju 53 cm vs Shotokan 92 cm = **diferença de 39 cm** (57% redução de área), confirmando que praticantes Gōjū-ryū executam *neko-ashi-dachi* mesmo quando instruídos no nome canônico Shōtōkan *kōkutsu-dachi*. Validação quantitativa do protocolo style-adaptive.

Tabela `COM height (m) × base × style`:
```
style       Goju-Ryu  Shotokan  Wado-Ryu
base
KIB           0.601     0.717     0.755   ← contraste-bomba
KOK           0.710     0.740     0.792
ZEN           0.682     0.735     0.803
```

KIB Goju 0,60 m vs Shotokan 0,72 m = **diferença de 12 cm**, consistente com *shiko-dachi* Naha-te (45° pés fora, fêmures girados internamente, COM mais baixo) vs *kiba-dachi* Shōtōkan.

---

## 6. Decisões metodológicas-chave (e suas justificativas)

| Decisão | Alternativa | Por que escolhi |
|---|---|---|
| Python como linguagem | MATLAB | Open-source, sem licença, reprodutível por qualquer revisor |
| Input: `_pose_filt_0.c3d` | `_pose_0.c3d` raw | Theia 20 Hz é validado (Kanko 2021a,b); raw também released para liberdade |
| Inertia: Theia gender-specific | Dempster genérico | Theia params são specific-ao-Theia-model; Visual3D usa Dempster para cross-check |
| Strike auto-detect (10% peak) | Threshold manual | Robusto a variação inter-sujeito; consistente entre trials |
| Janelas 1-3s e 6-9s | 0-3s e 6-9s | Excluir 1º segundo elimina perturbação de assumir a postura |
| ISB Wu 2002/2005 | Outros sistemas | Padrão de facto na biomecânica clínica e esportiva |
| KUK→KOK no loader | Renomear arquivos | Preserva fonte de origem; correção transparente |

---

## 7. Limitações conhecidas

1. **STATIC ausente em ID003-ID005** — primeira sessão piloto sem reference. Tratados via normalização do primeiro segundo do trial.
2. **Cotovelo ROM dinâmico** sofre gimbal lock em movimentos amplos (Euler degeneracy); janelas estáticas pre/post-strike não são afetadas.
3. **Pelvis/pelvis_shifted sem inertia** no Theia model — massa absorvida em thorax+thighs no modelo Theia (decisão deles). Diferença vs Dempster fica nos 12 mm observados.
4. **Wadō-ryū n=1** (ID004) — descritivo apenas, sem inferência possível.
5. **Cinética não integrada ainda** — force plates virão depois; quando integrar, adiciono COP-COM, MoS, RSR ao wide CSV.

---

## 8. Reprodutibilidade

Para reproduzir os 3 CSVs do zero:

```bash
# 1. Clonar repo
git clone https://github.com/luiz-pavani/karate-stances-dataset-scripts
cd karate-stances-dataset-scripts

# 2. Instalar deps
pip install -e .

# 3. Rodar pipeline (gera os 5 outputs em ./output)
python -m kds.batch \
  --data-root "/path/to/Kinematic Data" \
  --output-dir ./output

# 4. Consolidar para análise (gera 3 CSVs em data/processed_summary/)
python src/python/build_analysis_csv.py
```

Versão exata da pipeline usada: **v0.2.0** + commit `744a96c` (2026-05-14).

---

## 9. Próximos passos

- [ ] Integrar cinética (force plates) quando tu mandares — produz v0.3.0
- [ ] Adicionar análise estatística inferencial (Linear Mixed-Effects Models) ao Cap 1 — separado deste pipeline
- [ ] Bumpar Figshare para release público quando manuscrito Cap 2 estiver pronto para submissão *Scientific Data*

---

*Documento gerado a partir da execução real da pipeline em 2026-05-14/15. Path do repo: `/Users/judo365/Documents/MASTER ESPORTES/SMAART PRO/REPOS/karate-stances-dataset-scripts`. Path da pasta DATASET: `/Users/judo365/Documents/MASTER ESPORTES/MESTRADO/Artigos/DATASET/`.*
