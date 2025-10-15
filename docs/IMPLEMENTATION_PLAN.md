# Implementation Plan: ML-Based Footnote Classification

**Based on:** Comprehensive NLP research (see `RESEARCH_TEXT_CLASSIFICATION_METHODS.md`)

**Goal:** Replace rule-based heuristics with data-driven ML classifier optimized for F1 score

---

## Current State

**What We Have:**
- 3 test PDFs (Jackson_2014, Green_Roiphe_2020, Nedrud_1964)
- Docling PDF extraction working
- Rule-based citation filter (`extract_body_only.py`)
  - Current performance: ~20% removal rate
  - Issues: Misses "Cf.", "Compare", "E.g." patterns, arbitrary 20% threshold

**What We Learned:**
- Citation density alone is poor discriminator (69% of footnotes <10% density)
- Need data-driven approach: gather empirical priors from labeled corpus
- HTML law reviews provide ground truth labels for free

---

## Recommended Approach: Staged Development

### Phase 1: Data Collection & Feature Discovery (Week 1)

#### 1A: Scrape HTML Law Review Articles

**Objective:** Build labeled training corpus from HTML ground truth

**Target journals** (accessible online):
- Harvard Law Review (https://harvardlawreview.org/)
- Stanford Law Review (https://review.law.stanford.edu/)
- Yale Law Journal (https://www.yalelawjournal.org/)
- Columbia Law Review (https://columbialawreview.org/)

**Scraping script:**
```python
# scrape_law_reviews.py
from bs4 import BeautifulSoup
import requests
import pandas as pd
from pathlib import Path

def extract_from_html_article(url):
    """Extract body paragraphs and footnotes from HTML law review article."""
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    data = []

    # Body paragraphs (not in footnotes)
    for p in soup.find_all('p'):
        if not p.find_parent(class_='footnote') and not p.find_parent('aside'):
            text = p.get_text().strip()
            if len(text) > 50:  # Filter very short paragraphs
                data.append({'text': text, 'label': 'body_text', 'source': url})

    # Footnotes (various HTML patterns)
    footnote_selectors = ['.footnote', 'aside', '[role="note"]', '.note']
    for selector in footnote_selectors:
        for fn in soup.select(selector):
            text = fn.get_text().strip()
            if len(text) > 20:
                data.append({'text': text, 'label': 'footnote', 'source': url})

    return data

# Collect from multiple articles
articles = [
    # Add URLs manually or scrape index pages
]

all_data = []
for url in articles:
    try:
        data = extract_from_html_article(url)
        all_data.extend(data)
        print(f"✓ {url}: {len(data)} paragraphs")
    except Exception as e:
        print(f"✗ {url}: {e}")

# Save corpus
df = pd.DataFrame(all_data)
df.to_csv('data/html_law_review_corpus.csv', index=False)
print(f"\nTotal: {len(df)} labeled paragraphs")
print(f"  Body text: {len(df[df['label']=='body_text'])}")
print(f"  Footnotes: {len(df[df['label']=='footnote'])}")
```

**Target:** 50-100 articles → 5,000-10,000 labeled paragraphs

#### 1B: Feature Discovery via PMI/Chi-Squared

**Objective:** Discover discriminative words/patterns statistically

**Script:**
```python
# discover_features.py
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_selection import chi2
import numpy as np
import pandas as pd

# Load corpus
df = pd.read_csv('data/html_law_review_corpus.csv')
X = df['text']
y = (df['label'] == 'footnote').astype(int)

# Extract n-grams
vectorizer = CountVectorizer(
    ngram_range=(1, 3),  # Unigrams, bigrams, trigrams
    max_features=10000,
    min_df=5
)
X_counts = vectorizer.fit_transform(X)
feature_names = vectorizer.get_feature_names_out()

# Chi-squared test
chi2_scores, p_values = chi2(X_counts, y)

# Rank features
feature_scores = pd.DataFrame({
    'feature': feature_names,
    'chi2_score': chi2_scores,
    'p_value': p_values
}).sort_values('chi2_score', ascending=False)

# Top footnote indicators
print("\nTop 50 Footnote Indicators (Chi-Squared):")
print(feature_scores.head(50))

# Calculate PMI for top features
def calculate_pmi(feature, X, y):
    """Calculate Pointwise Mutual Information."""
    p_footnote = y.mean()
    p_body = 1 - p_footnote

    feature_mask = X[:, feature].toarray().flatten() > 0
    p_feature_given_footnote = y[feature_mask].mean() if feature_mask.sum() > 0 else 0
    p_feature_given_body = (1-y[feature_mask]).mean() if feature_mask.sum() > 0 else 0

    if p_feature_given_body > 0:
        pmi = np.log2(p_feature_given_footnote / p_feature_given_body)
    else:
        pmi = np.inf

    return pmi

# Calculate PMI for top 100 features
top_100_indices = np.argsort(chi2_scores)[-100:][::-1]
pmi_scores = [calculate_pmi(idx, X_counts, y) for idx in top_100_indices]

pmi_df = pd.DataFrame({
    'feature': [feature_names[idx] for idx in top_100_indices],
    'pmi': pmi_scores
}).sort_values('pmi', ascending=False)

print("\nTop 50 Footnote Indicators (PMI):")
print(pmi_df.head(50))

# Save results
feature_scores.to_csv('results/feature_importance_chi2.csv', index=False)
pmi_df.to_csv('results/feature_importance_pmi.csv', index=False)
```

**Expected discoveries:**
- "supra", "infra", "Id.", "ibid." (high PMI)
- "cf", "see also", "compare" (citation signals)
- Punctuation patterns (semicolons, periods)
- Case citation patterns

#### 1C: Analyze Citation Density Distribution

**Objective:** Find optimal threshold via empirical data

**Script:**
```python
# analyze_density_distribution.py
import matplotlib.pyplot as plt
import seaborn as sns
import re

def calculate_citation_density(text):
    """Calculate citation density using regex patterns."""
    patterns = [
        r'\d+\s+U\.S\.\s+\d+',
        r'\d+\s+S\.\s+Ct\.\s+\d+',
        r'\d+\s+F\.(2d|3d)\s+\d+',
        r'\(\d{4}\)',
        r'\bsupra note\s+\d+',
        r'\binfra note\s+\d+',
    ]

    citation_chars = sum(len(m.group()) for p in patterns for m in re.finditer(p, text))
    return citation_chars / max(1, len(text))

# Calculate densities
df['citation_density'] = df['text'].apply(calculate_citation_density)

# Visualize distributions
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Body text distribution
body_densities = df[df['label']=='body_text']['citation_density']
axes[0].hist(body_densities, bins=50, alpha=0.7, label='Body Text')
axes[0].set_xlabel('Citation Density')
axes[0].set_ylabel('Frequency')
axes[0].set_title('Body Text Citation Density Distribution')
axes[0].axvline(body_densities.mean(), color='r', linestyle='--', label=f'Mean: {body_densities.mean():.3f}')
axes[0].legend()

# Footnote distribution
footnote_densities = df[df['label']=='footnote']['citation_density']
axes[1].hist(footnote_densities, bins=50, alpha=0.7, label='Footnotes', color='orange')
axes[1].set_xlabel('Citation Density')
axes[1].set_ylabel('Frequency')
axes[1].set_title('Footnote Citation Density Distribution')
axes[1].axvline(footnote_densities.mean(), color='r', linestyle='--', label=f'Mean: {footnote_densities.mean():.3f}')
axes[1].legend()

plt.tight_layout()
plt.savefig('results/citation_density_distributions.png', dpi=300)

# Summary statistics
print("\nBody Text Citation Density:")
print(f"  Mean: {body_densities.mean():.3f}")
print(f"  Median: {body_densities.median():.3f}")
print(f"  95th percentile: {body_densities.quantile(0.95):.3f}")

print("\nFootnote Citation Density:")
print(f"  Mean: {footnote_densities.mean():.3f}")
print(f"  Median: {footnote_densities.median():.3f}")
print(f"  5th percentile: {footnote_densities.quantile(0.05):.3f}")

# Find optimal threshold (maximize F1)
from sklearn.metrics import f1_score

best_f1 = 0
best_threshold = 0

for threshold in np.arange(0.0, 0.30, 0.01):
    y_pred = (df['citation_density'] > threshold).astype(int)
    y_true = (df['label'] == 'footnote').astype(int)
    f1 = f1_score(y_true, y_pred)

    if f1 > best_f1:
        best_f1 = f1
        best_threshold = threshold

print(f"\nOptimal citation density threshold: {best_threshold:.3f}")
print(f"F1 score at optimal threshold: {best_f1:.3f}")
```

**Deliverable:** Evidence-based threshold replacing arbitrary 20%

---

### Phase 2: Baseline Model (Week 2)

#### 2A: Implement TF-IDF + SVM Classifier

**Objective:** Quick baseline with traditional ML

**Script:**
```python
# train_baseline_model.py
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import FunctionTransformer, StandardScaler
from sklearn.svm import LinearSVC
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
import joblib

# Load data
df = pd.read_csv('data/html_law_review_corpus.csv')
X = df['text']
y = (df['label'] == 'footnote').astype(int)

# Train/test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# Extract stylometric features
def extract_stylometric_features(texts):
    features = []
    for text in texts:
        citation_density = calculate_citation_density(text)
        words = text.split()
        features.append([
            len(words),  # Word count
            len(text.split('.')) / max(1, len(words)),  # Sentence length
            text.count(';') / max(1, len(text)),  # Semicolon density
            text.count('.') / max(1, len(text)),  # Period density
            citation_density,  # Citation density
            sum(1 for c in text if c.isupper()) / max(1, len(text)),  # Uppercase ratio
        ])
    return np.array(features)

# Build pipeline
pipeline = Pipeline([
    ('features', FeatureUnion([
        ('tfidf', TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 3),
            min_df=2
        )),
        ('stylometric', Pipeline([
            ('extract', FunctionTransformer(extract_stylometric_features, validate=False)),
            ('scale', StandardScaler())
        ])),
    ])),
    ('clf', LinearSVC(class_weight='balanced', C=1.0, max_iter=2000))
])

# Train
print("Training baseline model...")
pipeline.fit(X_train, y_train)

# Cross-validation
cv_scores = cross_val_score(pipeline, X_train, y_train, cv=5, scoring='f1')
print(f"\n5-Fold Cross-Validation F1: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")

# Evaluate
y_pred = pipeline.predict(X_test)
print("\nTest Set Performance:")
print(classification_report(y_test, y_pred, target_names=['body_text', 'footnote']))

# Confusion matrix
cm = confusion_matrix(y_test, y_pred)
print("\nConfusion Matrix:")
print(f"  TN: {cm[0,0]}, FP: {cm[0,1]}")
print(f"  FN: {cm[1,0]}, TP: {cm[1,1]}")

# Save model
joblib.dump(pipeline, 'models/baseline_svm_model.pkl')
print("\n✓ Model saved: models/baseline_svm_model.pkl")
```

**Expected performance:** F1 = 0.82-0.88 on HTML test set

#### 2B: Test on PDF Corpus

**Script:**
```python
# test_on_pdfs.py
import joblib

# Load model
model = joblib.load('models/baseline_svm_model.pkl')

# Extract from PDFs
pdf_texts = []
pdf_labels = []

for pdf_file in ['Jackson_2014.pdf', 'Green_Roiphe_2020.pdf', 'Nedrud_1964.pdf']:
    # Use existing body_extraction results as pseudo-labels
    all_text = Path(f'results/body_extraction/{pdf_file.stem}_default_all.txt').read_text()
    body_text = Path(f'results/body_extraction/{pdf_file.stem}_default_body_only.txt').read_text()
    footnote_text = Path(f'results/body_extraction/{pdf_file.stem}_default_footnotes_only.txt').read_text()

    # Split into paragraphs
    for para in body_text.split('\n\n'):
        if len(para) > 50:
            pdf_texts.append(para)
            pdf_labels.append('body_text')

    for para in footnote_text.split('\n\n'):
        if len(para) > 50:
            pdf_texts.append(para)
            pdf_labels.append('footnote')

# Predict
y_pdf_true = [1 if l=='footnote' else 0 for l in pdf_labels]
y_pdf_pred = model.predict(pdf_texts)

print("PDF Test Set Performance:")
print(classification_report(y_pdf_true, y_pdf_pred, target_names=['body_text', 'footnote']))
```

**Expected performance:** F1 = 0.75-0.85 (lower due to HTML→PDF distribution shift)

---

### Phase 3: Domain Adaptation (Week 3)

#### 3A: Fine-tune DistilBERT (Optional - if you have GPU)

**Setup:**
```bash
pip install transformers datasets torch accelerate
```

**Script:**
```python
# train_transformer.py
from transformers import (
    DistilBertTokenizer,
    DistilBertForSequenceClassification,
    Trainer,
    TrainingArguments
)
from datasets import Dataset
from sklearn.metrics import accuracy_score, f1_score

# Prepare data
tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')

def tokenize_function(examples):
    return tokenizer(examples['text'], padding='max_length', truncation=True, max_length=512)

train_dataset = Dataset.from_pandas(df_train).map(tokenize_function, batched=True)
test_dataset = Dataset.from_pandas(df_test).map(tokenize_function, batched=True)

# Load model
model = DistilBertForSequenceClassification.from_pretrained('distilbert-base-uncased', num_labels=2)

# Training
training_args = TrainingArguments(
    output_dir='./distilbert_results',
    num_train_epochs=3,
    per_device_train_batch_size=16,
    evaluation_strategy='epoch',
    save_strategy='epoch',
    learning_rate=2e-5,
    load_best_model_at_end=True,
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=test_dataset,
)

trainer.train()
model.save_pretrained('models/distilbert_footnote_classifier')
```

**Expected performance:** F1 = 0.88-0.93

#### 3B: Collect Small Labeled PDF Dataset

**Manual labeling script:**
```python
# label_pdf_samples.py
import random

# Load PDF paragraphs
pdf_paras = # ... extracted paragraphs

# Sample uncertain cases
uncertain_samples = random.sample(pdf_paras, 100)

# Interactive labeling
labels = []
for i, text in enumerate(uncertain_samples):
    print(f"\n[{i+1}/100]")
    print(text[:200] + "...")
    label = input("Label (b=body, f=footnote, s=skip): ").strip().lower()

    if label in ['b', 'f']:
        labels.append({'text': text, 'label': 'footnote' if label=='f' else 'body_text'})

# Save
pd.DataFrame(labels).to_csv('data/manually_labeled_pdf_samples.csv', index=False)
```

**Target:** 100-200 manually labeled PDF examples

---

### Phase 4: Ensemble & Deployment (Week 4)

#### 4A: Build Hybrid Ensemble

**Combine:**
1. Rule-based patterns (high-confidence cases)
2. TF-IDF + SVM (fast baseline)
3. DistilBERT (semantic understanding) - optional if GPU available

**Script:** See `ensemble.py` in research report

#### 4B: Integrate with Existing Pipeline

**Update `extract_body_only.py`:**
```python
# Instead of hardcoded is_likely_citation() function:
import joblib
ml_classifier = joblib.load('models/baseline_svm_model.pkl')

def classify_with_ml(text):
    """Use ML model instead of heuristics."""
    prediction = ml_classifier.predict([text])[0]
    return prediction == 1  # 1 = footnote

# In main extraction loop:
for item, level in doc.iterate_items():
    label = str(item.label)
    text = item.text

    if 'footnote' in label.lower():
        footnote_parts.append(text)
    elif classify_with_ml(text):  # ← ML-based classification
        footnote_parts.append(text)
    elif label.lower() in ['text', 'section_header', 'list_item', 'paragraph']:
        body_text_parts.append(text)
```

---

## Deliverables

**Data:**
- `data/html_law_review_corpus.csv` - Labeled training corpus (5K-10K examples)
- `data/manually_labeled_pdf_samples.csv` - PDF test set (100-200 examples)

**Models:**
- `models/baseline_svm_model.pkl` - TF-IDF + SVM baseline
- `models/distilbert_footnote_classifier/` - Fine-tuned DistilBERT (optional)
- `models/ensemble_model.pkl` - Hybrid ensemble

**Analysis:**
- `results/feature_importance_chi2.csv` - Top discriminative features (Chi-squared)
- `results/feature_importance_pmi.csv` - Top discriminative features (PMI)
- `results/citation_density_distributions.png` - Empirical density distributions
- `results/confusion_matrices/` - Model performance visualizations

**Code:**
- `scrape_law_reviews.py` - HTML corpus collection
- `discover_features.py` - Feature mining (PMI, Chi-squared)
- `train_baseline_model.py` - TF-IDF + SVM training
- `train_transformer.py` - DistilBERT fine-tuning (optional)
- `ensemble.py` - Hybrid model
- Updated `extract_body_only.py` - ML-integrated extraction

---

## Timeline

**Week 1**: Data collection + feature discovery → Evidence-based feature set
**Week 2**: Baseline model (TF-IDF + SVM) → F1 = 0.82-0.88
**Week 3**: Domain adaptation + PDF labeling → F1 = 0.85-0.92
**Week 4**: Ensemble + integration → F1 = 0.88-0.95

**Accelerated (if CPU-only):**
- Skip transformer fine-tuning
- Focus on rule-based + TF-IDF + SVM ensemble
- Target F1 = 0.85-0.92 in 2 weeks

---

## Success Metrics

**Compared to current heuristic:**
- Current: ~75-80% accuracy (estimated)
- Target: >90% accuracy (F1 > 0.90)
- Improvement: +10-15 percentage points

**Key metrics:**
- **Precision**: When we classify as footnote, how often are we right? (minimize false positives)
- **Recall**: Of all actual footnotes, what % do we catch? (minimize false negatives)
- **F1 Score**: Harmonic mean (balanced metric)

**Acceptable performance:**
- F1 > 0.85: Good
- F1 > 0.90: Excellent
- F1 > 0.95: Outstanding

---

## Next Immediate Steps

1. **Create data directory structure:**
   ```bash
   mkdir -p data models results/{features,confusion_matrices}
   ```

2. **Start HTML scraping** (highest priority):
   - Manually identify 20-30 accessible law review article URLs
   - Run `scrape_law_reviews.py`
   - Target: 5,000+ labeled paragraphs

3. **Run feature discovery:**
   - `discover_features.py` → Find top PMI/Chi-squared features
   - `analyze_density_distribution.py` → Optimal threshold

4. **Train baseline:**
   - `train_baseline_model.py` → Quick prototype
   - Test on existing PDF corpus

**Ready to start?** I can help implement any of these scripts!
