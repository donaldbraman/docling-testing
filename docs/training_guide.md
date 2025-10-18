# A Strategic Framework for Fine-Tuning ModernBERT for Document Layout Analysis in Legal Scholarship





### Executive Summary



This report provides a comprehensive, evidence-based framework for fine-tuning a ModernBERT model to perform text block classification on legal scholarship PDFs. The primary objective is to accurately classify text blocks to isolate `body_text`. This document directly addresses five critical questions regarding data requirements, class imbalance, and annotation schema design, synthesizing cutting-edge research with pragmatic implementation strategies.

The analysis culminates in five key recommendations:

1. **Data Collection:** Adopt an iterative data collection strategy. A baseline of **300-500 samples per class** is sufficient for a robust proof-of-concept, with a target of **1,000-2,000+ samples per class** for achieving production-grade performance. The highly structured nature of the legal domain significantly reduces the data requirements compared to general-domain text classification.
2. **Class Imbalance:** For class imbalance ratios exceeding **10:1**, which are expected in this domain, the primary mitigation strategy should be the implementation of **class weighting** within the model's loss function. This method is demonstrably superior to data resampling techniques for transformer models, as it avoids data duplication and the risk of overfitting on specific text sequences.
3. **Schema Granularity:** Employ a **comprehensive, 11-class annotation schema** from the project's outset. This approach leverages the principle of feature space partitioning, where defining a richer set of distinct classes improves the model's ability to discriminate between them. This paradoxically enhances the classification accuracy of the primary target class, `body_text`, by providing a clearer "negative space."
4. **Section Headings:** Establish a distinct **`section_heading`** class. Section headings possess unique logical, stylistic, and semantic properties. Merging this element with `body_text` would introduce significant noise, increase the variance within the `body_text` class, and ultimately degrade model performance.
5. **Rare Classes:** Initially merge rare classes such as `Table`, `Figure`, and `Equation` into a single, consolidated **`figure_table_equation`** class. This ensures sufficient training samples to maintain model stability and effective learning. Fine-grained distinction between these elements can be addressed post-deployment with a specialized second-stage model if required.

The following sections provide detailed justifications for these recommendations, grounded in empirical evidence and machine learning best practices. The report concludes with a unified, strategic roadmap for implementation, designed to guide the project from data annotation to model deployment.



## Section 1: Establishing Data Requirements for Robust Fine-Tuning



This section addresses the fundamental question of the minimum sample size required for effective fine-tuning. It moves beyond a single, universal number to provide a nuanced, risk-managed approach, contextualizing findings from the literature for the specific, highly-structured domain of legal scholarship.



### 1.1 The Spectrum of Data Needs for Transformer Fine-Tuning



The quantity of data required for fine-tuning a transformer model is not a fixed number but rather a spectrum influenced by task complexity, domain specificity, data quality, and the number of target classes.1 There is no single rule that applies to all scenarios.

At the high end of the spectrum, tasks involving sparse data with ambiguous or "messy" labels demand substantial datasets. For a 14-class classification problem, one analysis suggests a minimum of 2,000 examples per class (totaling 28,000) is necessary to begin fine-tuning, with performance exceeding 90% accuracy only after scaling to around 6,000 examples per class.2 This represents a challenging scenario characterized by high data variance and low label quality.

A more common and moderate recommendation for multi-class classification problems with fewer than 20 classes suggests a total dataset size between 1,000 and 10,000 samples.3 This aligns with other practical experiences where as few as 1,000 total samples for a 5-class problem (approximately 200 per class) yielded good results, though this was considered a lower bound for effective training.4

At the low end, for simply adapting a model to a highly specific task, some practitioners report that even 200-300 samples can be sufficient to achieve acceptable performance and "push the model in the direction you want".5 This aligns with the principles of few-shot learning, where models are adapted using very limited data.6 However, the task at hand is a standard fine-tuning operation, which involves updating a significant portion of the model's weights, rather than few-shot prompting, which primarily leverages the model's existing knowledge through carefully crafted inputs.8

The model in question, ModernBERT-base with 149 million parameters, is a powerful encoder model but is significantly smaller than multi-billion parameter Large Language Models (LLMs).2 As such, it still requires a non-trivial amount of data to adjust its parameters effectively without suffering from "catastrophic forgetting," where the model loses its general language understanding capabilities during specialization.10



### 1.2 The "Structured Domain" Advantage: Why Legal Scholarship Requires Less Data



The single most important factor influencing data requirements for this project is the nature of the domain: "legal scholarship" is described as "highly structured" with "consistent patterns." This structural consistency dramatically reduces the amount of data needed to achieve high performance.

The field of legal NLP has demonstrated that legal language possesses unique and learnable statistical properties. The development and success of domain-specific models like LegalBERT, which are pre-trained on large corpora of legal text (e.g., 12 GB), confirm that legal documents follow distinct linguistic and structural conventions.11 Fine-tuning a general-purpose model like ModernBERT on legal data serves to acclimate it to these specific nuances, making the learning process more efficient.14

Legal scholarship articles, in particular, adhere to a highly formulaic structure. They typically include a title, author block, abstract, an introduction, sequentially numbered sections with distinct headings, a conclusion, and a bibliography or reference section.15 This structural and stylistic consistency—for example, headings are formatted differently from body text, and footnotes have a predictable location and numbering scheme—means that the variance *within* each layout class is significantly lower than in general-domain text, such as social media posts or product reviews.

This low intra-class variance directly reduces the learning burden on the model. A model fine-tuned on a low-variance, high-structure dataset does not need to see as many examples to learn the defining features of a class. The patterns are stronger, more repetitive, and less ambiguous. This implies that the data requirements for this project will fall on the lower end of the spectrum identified in the previous section. The challenge is less about learning a wide variety of ways a class can appear and more about learning the subtle but consistent distinctions between a few well-defined classes.



### 1.3 A Pragmatic, Tiered Data Collection Strategy



Given the context of a structured domain, the most effective approach is not to aim for a single, large data collection target but to adopt an iterative, tiered strategy. This methodology allows for early validation of the model and schema, efficient use of annotation resources, and a clear path to scaling performance.

**Table 1: Data Collection Tiers for ModernBERT Fine-Tuning on Legal Scholarship DLA**

| **Tier** | **Objective**               | **Samples per Class** | **Total Samples (11 classes)** | **Expected Outcome**                                         | **Key Considerations**                                       |
| -------- | --------------------------- | --------------------- | ------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| **1**    | **Proof-of-Concept (PoC)**  | 300-500               | 3,300 - 5,500                  | Validate schema, confirm model learning, achieve baseline performance (>75% F1). | Focus on high-quality, consistent annotation. Verify that the pipeline is functional and classes are separable.17 |
| **2**    | **Production-Grade**        | 1,000 - 2,000         | 11,000 - 22,000                | Achieve robust, generalizable performance suitable for deployment (>90% F1). | Scale annotation efforts based on PoC findings. Address any class confusion identified in Tier 1. |
| **3**    | **State-of-the-Art (SOTA)** | 5,000+                | 55,000+                        | Maximize accuracy and minimize edge-case failures for mission-critical applications (>95% F1). | High annotation cost. Justified only if incremental gains are critical. Datasets of this scale are common in academic benchmarks.18 |



This tiered approach transforms the question from "how many samples?" to a strategic plan for iterative development, which is a recognized best practice in applied machine learning projects.3 It provides a framework for planning, budgeting, and setting realistic performance expectations at each stage of the project.



### 1.4 Deeper Implications of Domain Structure



The relationship between the quantity of data required and the structure of the domain is fundamentally inversely proportional. The more structured, formulaic, and consistent the domain, the fewer examples are needed to achieve a given level of performance. Fine-tuning is the process of teaching a pre-trained model the specific patterns of a downstream task. The complexity of this process is a function of the variance of the patterns within each class. A high-variance domain, such as classifying informal user reviews, requires many examples to capture all the different ways a concept can be expressed. In contrast, legal scholarship exhibits low variance; a `footnote` in one law review article is structurally and positionally very similar to a `footnote` in another, as dictated by strict style guides.16 Because this "pattern" for each class is more stable, it requires fewer examples for the model to learn its representative feature vector. This provides confidence that starting with the Tier 1 data size is a sound strategy, whereas a project in a less structured domain might need to begin at Tier 2.

Furthermore, in a structured domain, data quality—particularly annotation consistency—is more critical than raw quantity. The "Garbage In, Garbage Out" principle is a well-established axiom in machine learning.10 In a domain with subtle but consistent differences between classes (e.g., a `section_heading` versus a `title`), inconsistent labeling (for instance, sometimes labeling a subsection heading as `body_text`) will introduce significant noise. This noise directly contradicts the inherent structure of the data, forcing the model to learn incorrect or conflicting patterns and undermining the domain's natural advantage. Consequently, investing resources in a rigorous annotation guide and a robust quality control process for a Tier 1 dataset will yield a better return on investment than quickly collecting a larger but noisier Tier 2 dataset. This underscores the importance of establishing a clear and unambiguous annotation schema, as discussed in Section 3, before any large-scale data collection begins.



## Section 2: A Decision Framework for Managing Class Imbalance



This section provides a clear, actionable framework for addressing the severe class imbalance inherent in the legal document dataset. It defines quantitative thresholds for intervention and recommends the most suitable mitigation techniques for transformer-based text classification.



### 2.1 Quantifying the Problem: When Does Imbalance Become Critical?



Class imbalance is a prevalent issue in real-world datasets where the number of examples in one class (the majority class) significantly outnumbers the examples in another (the minority class). This disparity can cause standard machine learning models, which are often optimized for overall accuracy, to become biased towards the majority class, resulting in poor predictive performance for the minority class.20 The user's example of 100 `body_text` blocks for every 1 `title` block represents a 100:1 ratio, a clear case of severe imbalance.

The standard metric for quantifying this issue is the **Imbalance Ratio (IR)**, defined as the number of samples in the majority class divided by the number of samples in the minority class.23 An analysis of existing research provides clear thresholds for when this ratio becomes problematic:

- An IR as low as **4.3** (1,654 majority vs. 383 minority samples) has been identified as high enough to introduce significant bias into machine learning models.24
- In a sentiment analysis project, an 80/20 class split, corresponding to an IR of **4**, was sufficient to cause a BERT model to almost exclusively predict the majority class.25
- A study on scientific paper classification identified a 12/88 split (IR of approximately **7.3**) as the central challenge that required specialized handling techniques.26
- In some contexts, model performance has been observed to degrade abruptly at an IR of just **2**.27

Based on this evidence, a clear decision framework can be established. An **IR greater than 10** should be considered a severe imbalance that necessitates a mitigation strategy. For IRs between **5 and 10**, mitigation is strongly recommended to prevent model bias. The user's anticipated IR of 100 is far beyond this critical threshold and absolutely requires intervention.



### 2.2 A Comparative Analysis of Mitigation Techniques: Weighting vs. Resampling



Two primary families of techniques are used to address class imbalance: data-level methods, which modify the dataset itself (resampling), and algorithm-level methods, which adjust the model's learning process (cost-sensitive learning or class weighting).22 For text classification tasks using transformer models, the choice between these methods is not arbitrary; algorithm-level methods are demonstrably superior.

**Data-Level Resampling Techniques:**

- **Random Undersampling:** This method involves randomly removing samples from the majority class to balance the dataset. Its major drawback is the loss of potentially valuable data, which is especially detrimental when the overall dataset size is limited.28
- **Random Oversampling:** This technique randomly duplicates samples from the minority class. While it balances class counts, it presents a significant risk for text classification: the model is exposed to the exact same text sequences multiple times, which does not introduce new information and can lead to severe overfitting on those specific examples.30
- **Synthetic Minority Over-sampling Technique (SMOTE):** SMOTE generates new, synthetic samples by interpolating between existing minority class samples in the feature space.28 This approach is fundamentally ill-suited for text data processed by transformers. SMOTE was designed for continuous, low-dimensional feature spaces. Applying it to the high-dimensional, sparse, and semantically rich embeddings produced by models like ModernBERT can create nonsensical "Frankenstein" text blocks whose embeddings do not correspond to any valid linguistic or structural patterns.32

**Algorithm-Level Class Weighting:**

- **Mechanism:** This technique modifies the model's loss function (typically cross-entropy) to apply a higher penalty when the model misclassifies an example from a minority class.32 Instead of showing the model more minority examples, this method makes mistakes on those examples more "costly," forcing the model to pay more attention to them during training.

- Implementation: Most modern training frameworks, including the Hugging Face Trainer API, provide built-in support for class weights.25 The weights are typically calculated as being inversely proportional to the class frequencies. A common formula for the weight wj of a class j is:



  $$w_j = \frac{N}{C \times N_j}$$



  where N is the total number of samples, C is the number of classes, and Nj is the number of samples in class j.35

- **Advantages for Transformers:** Class weighting is the most effective and theoretically sound solution for this task. It avoids the pitfalls of resampling by not altering the original data distribution. It directly targets the optimization objective, which is the root cause of the bias, and has been shown to be highly effective for transformer models like RoBERTa (a close relative of BERT) in imbalanced settings.36

**Table 2: Comparative Analysis of Class Imbalance Mitigation Techniques for Text Classification**

| **Technique**            | **Mechanism**                                                | **Impact on Training Data** | **Computational Cost** | **Suitability for Text Transformers** | **Key Risk**                                                 |
| ------------------------ | ------------------------------------------------------------ | --------------------------- | ---------------------- | ------------------------------------- | ------------------------------------------------------------ |
| **Random Undersampling** | Removes samples from the majority class.                     | Reduces dataset size.       | Low                    | Poor                                  | **Information Loss:** Discards potentially valuable training data. |
| **Random Oversampling**  | Duplicates samples from the minority class.                  | Increases dataset size.     | Low                    | Poor                                  | **Overfitting:** Model memorizes specific text sequences.    |
| **SMOTE**                | Creates synthetic minority samples via interpolation.        | Increases dataset size.     | Moderate               | Very Poor                             | **Artifact Generation:** Creates nonsensical, out-of-distribution text embeddings. |
| **Class Weighting**      | Modifies the loss function to penalize minority class errors more heavily. | None.                       | Negligible             | Excellent                             | **Hyperparameter Sensitivity:** Extreme weights can cause over-correction and bias towards the minority class.37 |





### 2.3 Deeper Implications of Method Selection



The choice between resampling and class weighting is a strategic decision dictated by the nature of the data and the model architecture. For high-dimensional, semantic data like the text embeddings generated by transformers, modifying the loss function is fundamentally safer and more effective than modifying the data points themselves. A transformer model learns a rich, contextual representation of each text block in a high-dimensional vector space. Oversampling forces the model to re-learn from identical vector representations, which provides diminishing returns and encourages overfitting to those specific points in the feature space. SMOTE, which operates by creating points "between" existing points, is conceptually flawed for text; the "average" of the embeddings for "The court finds..." and "The plaintiff argues..." does not necessarily correspond to any valid, semantically coherent legal text. It creates out-of-distribution artifacts that can confuse the model.

Class weighting, in contrast, does not tamper with the data representation. It operates on the model's output—the loss. It effectively tells the model, "Your representation for this rare `abstract` class led to a mistake, and because this class is rare, this mistake is 50 times more costly than a mistake on `body_text`." This strong signal incentivizes the model to adjust its internal parameters to create a more accurate and separable representation for the minority class without being exposed to artificial or duplicated data.

Furthermore, the goal of imbalance handling is not necessarily to achieve a perfect 1:1 balance, but to ensure that the minority classes contribute meaningfully to the training loss. Some studies have found that a perfectly balanced 50:50 distribution is not always optimal for learning.21 The true distribution of classes in the real world is itself a useful signal for the model, providing a prior probability for each class.20 Completely erasing this signal through aggressive resampling might harm the model's calibration and performance on real-world data. Class weighting elegantly solves this by amplifying the learning signal from rare classes during training while allowing the model to be evaluated on the true, imbalanced data distribution in the validation and test sets. This provides a more realistic assessment of the model's performance and is the recommended approach.



## Section 3: Designing a Purpose-Built Annotation Schema



This section provides a comprehensive answer to the three questions related to class definition: granularity, the handling of section headings, and the treatment of rare classes. It advocates for a comprehensive initial schema, justifying this approach by explaining how a richer set of classes enhances feature space partitioning and ultimately improves the classification of the target `body_text` class.



### 3.1 Granularity Strategy: The Case for a Comprehensive Initial Schema



The primary goal of this project is to accurately extract `body_text`. A common but flawed intuition is to simplify the problem by starting with a minimal set of classes (e.g., `title`, `body_text`, `footnote`) and adding more later. However, a counterintuitive but powerful principle in classification is that adding more well-defined classes can significantly improve the model's ability to identify a specific target class. This is due to a phenomenon that can be described as **"negative space definition"** or **"feature space partitioning."**

An iterative approach, where elements like `abstract`, `author`, and `section_heading` are initially merged into the `body_text` class, would be detrimental. This would create a highly varied and noisy "mega-class" containing structurally and semantically distinct elements. The model would be forced to learn a single, diffuse representation for all these different types of text blocks, increasing the intra-class variance and making the decision boundary for true `body_text` fuzzy and unreliable.39

Conversely, by defining a richer set of 10-11 classes from the start, the model is forced to learn the specific features that differentiate each class from all others. To correctly classify an `abstract`, the model must learn that it is *not* a `title` and also *not* `body_text`. This process of learning to separate these related-but-distinct classes carves out a much more precise, well-defined, and smaller volume in the feature space that is exclusively occupied by the actual `body_text` class. This makes `body_text` easier to identify and reduces misclassifications from neighboring classes.

This principle is validated by the design of major Document Layout Analysis (DLA) datasets. DLA is fundamentally about identifying distinct structural elements to convert unstructured documents into structured, machine-readable formats.40 To this end, established benchmarks like DocLayNet use a detailed set of 11 classes, and the D4LA dataset uses 27 classes.19 This granularity is not superfluous; it is necessary to accurately capture the document's structure. Adopting a coarse schema would defeat the core purpose of the layout analysis task.



### 3.2 Integrating Section Headings: A Structural and Semantic Imperative



The user correctly identifies that `section headings` (e.g., "I. Introduction," "II. Background") are a distinct structural element in legal articles. The question of whether to merge them with `body_text` is critical.

**Recommendation: Create a Separate `section_heading` Class.**

This recommendation is based on several key justifications:

1. **Logical Role:** Section headings serve a distinct logical role in the document's hierarchy. They are subordinate to the main `title` but are hierarchically superior to the `body_text` paragraphs they introduce.15 Standard DLA schemas consistently treat headings and titles as separate logical categories, distinct from general paragraph text.42
2. **Stylistic and Positional Features:** Law review style guides mandate specific and consistent formatting for headings, often involving different fonts, sizes, capitalization, bolding, and spacing, all of which distinguish them from standard body text.16 These visual and stylistic cues are critical features for a layout-aware model to learn.
3. **Semantic Content:** Headings function as meta-text; they describe the content of the subsequent paragraphs. Their language is typically topical, concise, and structural, differing significantly from the dense, argumentative, and citation-heavy language that characterizes `body_text`.
4. **Maintaining Low Intra-Class Variance:** Merging headings with body text would introduce a second, distinct pattern into the `body_text` class. This would increase its internal variance and make it harder for the model to learn a clean, cohesive representation, directly contradicting the principle of feature space partitioning.



### 3.3 A Pragmatic Approach to Rare Classes (Equations, Tables, Figures)



The user notes that classes such as `Equation`, `Table`, and `Figure` appear in fewer than 5% of documents. This presents a classic rare class problem, where there may be too few examples to train a stable and reliable classifier for each one individually.47

**Recommendation: Merge these into a Single `figure_table_equation` Class for Initial Training.**

This strategy is justified for the following reasons:

1. **Data Aggregation:** While semantically different, these three elements share key structural characteristics: they are typically non-prose blocks, are often centered or set apart from the main text, frequently have associated captions, and serve to break the continuous flow of `body_text`. Grouping them allows for the aggregation of their sparse samples into a single, more statistically significant class. This is a form of concept decomposition, where related rare concepts are grouped to make them more learnable for the model.49
2. **Model Stability:** Training a model with classes that have very few samples (e.g., fewer than 100) can lead to extreme overfitting on those few examples and can destabilize the learning process for the entire model.47 A single, more populated `figure_table_equation` class provides a clearer and more stable learning signal.
3. **Alignment with Primary Goal:** The main objective of the project is to isolate `body_text`. A single, unified class for all major non-prose block elements effectively achieves this separation without risking the model's stability over a secondary goal (distinguishing a table from a figure).
4. **Pathway for Future Refinement:** This initial merging does not preclude future granularity. If, post-deployment, a business need arises to distinguish between these elements, a second-stage classifier can be developed. This would be a smaller, specialized model applied only to blocks already identified as `figure_table_equation`—a much simpler and more constrained classification task. This aligns with iterative development principles, where complexity is added as needed rather than all at once.50



### 3.4 Deeper Implications of Schema Design



The optimal annotation schema is not defined by human intuition alone but by the objective of creating maximally separable class clusters for the machine learning model. A well-designed schema is one that **minimizes intra-class variance** (examples within a class are very similar to each other) and **maximizes inter-class variance** (examples from different classes are very different from each other).

The goal of a classification model is to learn decision boundaries that separate classes in a high-dimensional feature space. The "easier" the geometry of this separation problem, the better the model will perform. "Easy" geometry means the clusters of data points for each class are tight and compact (low intra-class variance) and are located far apart from each other (high inter-class variance).

Every decision about the schema should be evaluated against this principle. For example, merging `section_heading` into `body_text` creates a single class with two distinct centers of gravity in the feature space (one for the short, bold, centered headings and another for the long, justified paragraphs). This results in a diffuse, non-convex cluster with high intra-class variance, making the geometric separation problem "hard" for the model. Separating them into two classes creates two tighter, more distinct clusters, making the geometry "easy."

Similarly, attempting to train a `table` class with only 50 samples would result in a tiny, poorly defined cluster that might easily overlap with other classes due to insufficient data to define its boundaries. Merging it with `figure` and `equation` creates a larger, more stable cluster for the `figure_table_equation` class, improving the overall geometric problem that the classifier must solve. Therefore, every schema design choice should be interrogated with the question: "Does this make the geometric separation problem easier for the model?"



## Section 4: Synthesis and Strategic Implementation Roadmap



This final section consolidates all preceding recommendations into a unified, step-by-step guide for project implementation. It presents the final proposed annotation schema and outlines a complete workflow from data sampling and annotation to model training and evaluation.



### 4.1 The Final Proposed Annotation Schema



Based on the analysis in Section 3, a comprehensive 11-class schema is proposed. This schema is informed by best practices from established DLA datasets like DocLayNet 19 and is specifically adapted for the common structures found in legal scholarship documents.15 This detailed schema is designed to ensure high-quality, consistent annotations, which are critical for model performance.

**Table 3: Final Proposed Annotation Schema for Legal Scholarship DLA**

| **Class Name**              | **Definition**                                               | **Annotation Guidelines & Examples**                         |
| --------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| **`title`**                 | The main title of the article.                               | The primary, most prominent heading at the beginning of the document. Excludes subtitles or journal information. |
| **`author`**                | Author names, affiliations, and acknowledgments.             | Typically found directly below the title. Includes university affiliations, author notes, and grant acknowledgments. |
| **`abstract`**              | The formal abstract section preceding the main text.         | A distinct, single-paragraph summary of the article, often labeled "Abstract" or stylistically indented. |
| **`section_heading`**       | Numbered or titled section and subsection headers.           | Any text that serves as a structural heading for a subsequent block of text. Examples: "I. Introduction", "A. Historical Context", "1. Statutory Analysis". |
| **`body_text`**             | The main paragraphs of the article's argumentative structure. | The primary prose of the document, excluding all other defined categories. This is the main target class for extraction. |
| **`footnote`**              | Footnote text appearing at the bottom of the page.           | Includes the footnote number and the full text of the footnote. Does not include the in-text citation number. |
| **`bibliography`**          | The list of references or bibliography at the end of the article. | The entire section containing the list of cited works, often labeled "Bibliography," "References," or "Works Cited." |
| **`header`**                | Running headers at the top of the page.                      | Repetitive text at the top of most pages, such as the journal name, volume number, or author's last name. |
| **`footer`**                | Running footers at the bottom of the page.                   | Repetitive text at the bottom of the page, typically page numbers if they are not part of the footnote section. |
| **`figure_table_equation`** | A merged class for tables, figures, images, or standalone equations. | Includes the object itself (table, image, etc.) and its associated caption or title (e.g., "Table 1:", "Figure 2:"). |
| **`list_item`**             | Bulleted or numbered lists within the body of the text.      | Each item in a list should be labeled individually. This helps distinguish structured lists from standard prose paragraphs. |



### 4.2 Step-by-Step Implementation Plan



This plan outlines a phased approach to developing the document layout classifier, starting with a proof-of-concept and scaling to a production-ready model.



#### Phase 1: Dataset Curation and Annotation (Tier 1)



1. **Document Sampling:** Begin by randomly sampling a set of documents from the available HTML-PDF corpus. From these documents, extract all text blocks and their corresponding ground-truth labels based on the HTML structure.
2. **Targeted Collection:** The goal is to collect **300-500 examples for each of the 11 classes** defined in Table 3. For high-frequency classes like `body_text` and `footnote`, this target will be met quickly. For rarer classes like `abstract` or `author`, a targeted sampling approach will be necessary. This may involve specifically searching for documents that contain these elements to ensure the minimum threshold is met for every class.
3. **Annotation Quality Control:** Develop a detailed annotation guide based on the definitions in Table 3. To ensure consistency, have at least two annotators independently label a small, shared subset of documents. Measure the inter-annotator agreement (e.g., using Cohen's Kappa) and resolve any discrepancies by refining the guidelines until a high level of agreement is achieved.



#### Phase 2: Model Fine-Tuning



1. **Environment Setup:** Utilize the Hugging Face `transformers` library for model loading and training.25 Load the `modernbert-embed-base` model using `AutoModelForSequenceClassification`, ensuring it is configured with `num_labels=11` to match the schema.52
2. **Handling Class Imbalance:** After creating the Tier 1 training set, calculate the frequency of each of the 11 classes. Use a standard utility, such as `sklearn.utils.class_weight.compute_class_weight` with the `class_weight='balanced'` setting, to compute the appropriate weights for each class.25 These weights must be passed to the loss function during training. This typically requires creating a custom `Trainer` class that incorporates a weighted cross-entropy loss function.37
3. **Hyperparameter Configuration:** Begin with hyperparameters that are well-established for fine-tuning BERT-like models: a learning rate in the range of $2 \times 10^{-5}$ to $5 \times 10^{-5}$, a batch size of 16 or 32 (depending on GPU memory), and a training duration of 3 to 4 epochs.3 Employ a learning rate scheduler with a warmup period to stabilize training. A key advantage of ModernBERT is its ability to handle long sequences (up to 8,192 tokens), which is highly beneficial for processing dense legal text.9 However, this long context length significantly increases GPU memory consumption. If memory becomes a bottleneck, use gradient accumulation to simulate a larger batch size with less memory.53



#### Phase 3: Evaluation and Iteration



1. **Evaluation Metrics:** Do not rely solely on overall accuracy, as it can be misleading in an imbalanced setting. The primary evaluation metrics should be per-class and macro-averaged **F1-score, Precision, and Recall**.22 Generating a **confusion matrix** is essential for diagnosing specific areas of confusion between classes (e.g., is the model confusing `title` with `section_heading`?).55
2. **Analysis and Refinement:** Thoroughly analyze the performance of the model trained on the Tier 1 dataset. Identify which classes perform well and which are struggling. Use the confusion matrix to pinpoint specific error patterns. These insights should be used to refine the annotation guidelines or to identify if a particular class requires more diverse training examples.
3. **Scaling to Production:** If the proof-of-concept results are promising and validate the chosen schema, proceed to the next phase. Scale the data collection efforts to meet the Tier 2 target of **1,000-2,000 samples per class**. This larger, more comprehensive dataset will be used to train the final production-grade model, repeating the fine-tuning and evaluation process to ensure robust and generalizable performance.



### 4.3 Concluding Remarks



This report has outlined a robust, principled, and pragmatic approach to the document layout analysis task. The strategy is built on a foundation of empirical evidence from both academic research and industry best practices. By adopting a comprehensive and granular annotation schema, proactively managing class imbalance through class weighting, and following a tiered data collection strategy, the project is positioned for success. The highly structured nature of the legal scholarship domain is a significant advantage that, when properly leveraged through a well-designed schema and high-quality annotations, will enable the fine-tuning of a highly accurate ModernBERT classifier for the primary goal of `body_text` extraction.
