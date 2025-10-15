# Strategic Framework for Body Text Extraction in Legal Documents: A Comparative Analysis of Binary and Multiclass Training with ModernBERT





## Foundational Comparison: Binary vs. Multiclass Architectures for Body Text Isolation



The selection of a classification architecture—binary versus multiclass—is the most consequential strategic decision in developing a high-fidelity document segmentation model. This choice extends beyond the mere number of output classes; it fundamentally dictates the nature of the learning task, the structure of the model's internal feature representations, and its ultimate ability to generalize to unseen documents. For the specialized domain of legal scholarship, where documents possess a highly regularized and predictable structure, this decision carries even greater weight. A thorough analysis reveals that while a binary approach offers apparent simplicity, a multiclass framework provides a more robust and theoretically sound path toward achieving the primary objective: the precise and reliable isolation of `body` text.



### The Binary Approach (`body` vs. `not-body`): An Analysis of Simplicity and its Pitfalls



The binary classification approach frames the problem as a simple dichotomy: a given text block is either `body` or it is `not-body`.1 The model's objective is to learn a single, high-dimensional decision boundary, or hyperplane, that effectively separates all instances of the `body` class from the feature space occupied by every other type of text block.1 This method is computationally direct and requires a less complex annotation scheme, as every non-body element is collapsed into a single negative category. However, this simplicity masks profound underlying challenges that can severely limit model performance, particularly in a structured domain like legal document analysis.

The most significant deficiency of the binary approach is the creation of a heterogeneous, semantically incoherent negative class. The `not-body` category is not a unified concept but rather a "garbage can" or "catch-all" that amalgamates structurally and functionally distinct document elements.3 In the context of a legal scholarship PDF, this single `not-body` class indiscriminately groups together disparate components such as:

- **Footnotes:** Characterized by smaller font sizes, dense citation patterns (e.g., case names, journal volume numbers), and a specific location at the bottom of the page.5
- **Headers and Footers:** Highly repetitive text blocks containing page numbers, journal titles, or author names, appearing consistently at the top or bottom margins.5
- **Bibliography/References:** A highly structured list of citations, typically appearing at the end of the document, with a unique and consistent formatting style.5
- **Title and Author Information:** Unique text blocks at the beginning of the document with distinct font sizes and formatting.6
- **Tables, Figures, and Captions:** Elements with unique spatial layouts and content types that differ significantly from prose.5

This extreme heterogeneity within the `not-body` class presents a formidable learning challenge. The model is forced to construct a single, highly complex, and potentially convoluted decision boundary to cordon off the `body` class. It must learn that a text block is `not-body` for entirely different reasons—a footnote is rejected because of its citation syntax, a header is rejected because of its repetitive content and page position, and a table is rejected because of its columnar structure. Forcing a single class to represent these unrelated negative concepts pollutes the learning signal, encouraging the model to rely on brittle, superficial heuristics rather than developing a deep, semantic understanding of what positively defines `body` text.

Furthermore, this approach almost guarantees a severe class imbalance. In a typical legal article, the number of individual footnote, header, and reference blocks can easily exceed the number of main body text blocks. This results in the `not-body` class being the majority class by a large margin.3 A model trained naively on such data will quickly learn that it can achieve high accuracy by simply predicting `not-body` for every input, rendering it completely useless for the intended task.11 Consequently, standard accuracy becomes a dangerously misleading evaluation metric. To properly assess performance, one must rely on metrics that are robust to imbalance, such as Precision, Recall, F1-Score (particularly for the `body` class), and Balanced Accuracy, which account for the model's performance on the minority class.12



### The Multiclass Approach: Leveraging Structural Diversity for Enhanced Representation Learning



In contrast, a multiclass classification framework treats each distinct structural element of the document as its own unique class.1 Instead of learning a single boundary against a chaotic negative class, the model is tasked with learning a set of decision boundaries that separate every class from every other class. This can be implemented through strategies like One-vs-Rest (OvR), where K classifiers are trained to distinguish one class from all others, or One-vs-One (OvO), where ![img](data:,) classifiers are trained for each pair of classes.16 Modern neural network architectures, such as the one used in ModernBERT, typically handle this natively with a final layer that produces a probability distribution over all K classes.19

The fundamental advantage of the multiclass approach lies in its ability to induce a more structured and meaningful feature space through a process of **feature space partitioning**. By compelling the model to learn explicit decision boundaries not only between `body` and `footnote` but also between `footnote` and `header`, `header` and `bibliography`, and so on, we force it to discover the specific, discriminative features that uniquely define each class.21 The model must learn that the features distinguishing a `footnote` from a `header` (e.g., citation syntax vs. page number patterns) are different from the features that distinguish either of them from the main `body` text (e.g., prose continuity, paragraph structure). This process effectively carves the high-dimensional feature space into well-defined, semantically coherent regions, where each region corresponds to a specific document element.24

This structured partitioning has a direct and powerful benefit for the primary goal of identifying `body` text. The definition of the `body` class becomes sharper and more robust. It is no longer defined negatively by what it *is not* (i.e., not part of the `not-body` garbage can), but is instead defined positively through its contrast with other well-defined, coherent classes. The model learns a more precise representation of `body` text because its negative examples are specific and informative. When the model is penalized for misclassifying a `body` block as a `footnote`, it receives a clear signal to adjust its weights based on the specific features of footnotes. This is a far more effective learning signal than the ambiguous feedback from a generic `not-body` class. This process encourages the model to maximize the variance between classes (inter-class variance) while minimizing the variance within each class (intra-class variance), leading to cleaner separation and higher classification accuracy.23

While class imbalance may still exist among the various classes (e.g., there will likely be more `body` blocks than `abstract` blocks), the problem is significantly more manageable than in the binary case. The imbalance is distributed across several minority classes rather than being concentrated in a single, massive majority class versus a single minority class.3 This distribution makes corrective techniques, such as applying class weights during training, more stable and effective. Furthermore, the multiclass setup provides superior error analysis. A misclassification is no longer an ambiguous `body -> not-body` error; it becomes a specific `body -> footnote` or `body -> abstract` error. This provides a precise, actionable signal for debugging and model improvement, pointing directly to the types of features the model is struggling to differentiate.



### Synthesis and Recommendation: Why Multiclass Excels for Structured Documents



For document domains characterized by a high degree of structural regularity, such as legal scholarship, the multiclass approach is fundamentally superior. The consistent presence of distinct elements like footnotes, headers, and bibliographies is not a source of noise to be discarded but a rich source of structural information to be exploited. Multiclass training should therefore be viewed not merely as a classification strategy but as a powerful form of implicit representation learning and regularization that is perfectly suited for document layout analysis.

The core logic is as follows: The primary goal is to maximize the accuracy of `body` text identification. This requires the model to learn a robust, generalizable feature representation of what constitutes `body` text. A binary (`body` vs. `not-body`) framework provides a weak and noisy learning signal because the `not-body` class is an incoherent amalgamation of disparate concepts, leading to a diffuse and poorly defined decision boundary. In contrast, a multiclass framework (`body`, `footnote`, `header`, etc.) provides multiple strong, clear, and independent learning signals. To minimize its loss, the model is forced to learn the unique feature sets that define each of these distinct classes. This architectural constraint results in a more partitioned and semantically meaningful internal feature space. The vector representations for all `footnote` blocks will naturally cluster together, far from the `header` cluster, which in turn is distinct from the `body` cluster. This enforced separation of all classes as a direct consequence of the training objective results in a much cleaner, more reliable, and more accurate decision boundary for the `body` class itself. The model becomes better at identifying `body` text precisely because it has been forced to become an expert at identifying all the other structured elements of the document.

| Feature                          | Binary (`body` vs. `not-body`)                               | Multiclass (`body`, `footnote`, etc.)                        |
| -------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| **Feature Discrimination**       | **Low.** The model learns a single, complex boundary against a noisy negative class, often relying on superficial features. | **High.** The model must learn multiple boundaries, forcing the discovery of discriminative features unique to each class, which sharpens the definition of all classes. |
| **Handling of Negative Class**   | **Poor.** The `not-body` class is a heterogeneous "garbage can," providing a weak and ambiguous learning signal. | **Excellent.** Each non-body class is semantically coherent and distinct, providing specific and informative negative examples for the `body` class. |
| **Robustness to Imbalance**      | **Brittle.** Highly susceptible to bias towards a potentially massive `not-body` majority class, making training unstable. | **More Robust.** Class imbalance is distributed across multiple classes, making it more manageable with techniques like class weighting. |
| **Data Annotation Effort**       | **Lower.** Requires labeling text blocks into only two categories. | **Higher.** Requires more granular, per-class labeling, which increases initial data preparation costs. |
| **Computational Cost**           | **Lower.** The final classification layer has fewer output neurons (logits), and the loss calculation is simpler. | **Higher.** The final layer is larger, and the loss function must operate over a probability distribution for all K classes. |
| **Interpretability of Errors**   | **Difficult.** A misclassification of `body` as `not-body` is ambiguous and provides little insight into the cause of the error. | **High.** A misclassification of `body` as `footnote` provides a specific, actionable signal that the model is confused by features common to both, guiding targeted improvements. |
| **Suitability for Legal Domain** | **Sub-optimal.** Fails to leverage the inherent, predictable, and rich logical structure of legal scholarship documents. | **Optimal.** Explicitly models the document's logical structure, turning it into a powerful source of information for improving classification accuracy. |



## Initial Implementation Strategy: A Multiclass-First Approach



Based on the foundational analysis, the most effective and theoretically sound path forward is to begin directly with a multiclass classification model. This approach avoids the inherent limitations of a binary framework from the outset and establishes a more robust baseline upon which to build iterative improvements. It is not an experimental choice but a strategic one, designed to align the model's learning objective with the intrinsic structure of the target documents.



### Rationale for a Multiclass Baseline



Commencing with a multiclass model is the recommended strategy because it directly addresses the nature of the data. Legal scholarship articles are not an unstructured sea of text; they are meticulously structured documents with a consistent set of logical components.27 A multiclass framework allows the model to learn this structure explicitly, which, as established, is the most effective way to improve the definition and identification of the `body` class.

By starting with a multiclass architecture, the project immediately gains several advantages:

1. **Avoids the "Garbage Can" Problem:** It sidesteps the need to train a model against a noisy, heterogeneous `not-body` class, preventing the development of brittle, non-generalizable heuristics.
2. **Establishes a Stronger Foundation:** The feature representations learned by a multiclass model are inherently more discriminative and better organized. This provides a higher-quality starting point for subsequent fine-tuning and optimization phases.
3. **Leverages Domain Knowledge:** It directly encodes prior knowledge about the structure of legal documents into the model's design, aligning the machine learning task with the real-world data generation process.5



### Defining an Optimal Class Schema for Legal Scholarship



The effectiveness of a multiclass model is contingent on a well-designed class schema. The choice of labels represents a critical trade-off between granularity and data availability. A schema with too few classes risks collapsing distinct elements (e.g., merging `header` and `footer` into a single `marginalia` class), which would reintroduce the problem of heterogeneity on a smaller scale. Conversely, a schema with too many highly specific classes (e.g., `section_heading_level_1`, `section_heading_level_2`, `section_heading_level_3`) can lead to severe data scarcity for the rarer classes, making it difficult for the model to learn their features and increasing the cost and complexity of annotation.

Drawing from established style guides and common structures of law review articles, the following 10-class schema is proposed as a robust and balanced starting point for the legal scholarship domain 5:

1. **`Title`**: The main title of the article.
2. **`Author_Affiliation`**: Text blocks identifying the author(s) and their institutional affiliations.
3. **`Abstract`**: The summary paragraph that precedes the main text.
4. **`Body`**: The target class, comprising the main prose and paragraphs of the article.
5. **`Footnote`**: Footnotes or endnotes, typically appearing at the bottom of the page or end of the document.
6. **`Header`**: Repetitive text at the top of the page (e.g., journal name, volume number).
7. **`Footer`**: Repetitive text at the bottom of the page (e.g., page number).
8. **`Bibliography` / `References`**: The list of cited works, usually at the end of the article.
9. **`Table_Figure`**: This class should encompass tables, figures, images, and their associated captions to consolidate visually distinct, non-prose elements.
10. **`Equation`**: Formally presented mathematical equations.

This schema is designed to be comprehensive, capturing the major logical and structural components of a typical legal article. Each class is sufficiently distinct in its content, formatting, and/or position to provide a strong, independent signal to the model, thereby maximizing the benefits of feature space partitioning and enhancing the learned representation of the `Body` class.



### Configuring ModernBERT for Document Layout Analysis



The ModernBERT architecture is particularly well-suited for this task due to several key innovations. The most significant of these is its dramatically expanded context length of 8,192 tokens, a substantial increase from the 512-token limit of original BERT models.31 This large context window is a critical advantage for document layout analysis. It allows the model to process the entire text content of even very large document blocks in a single pass. More importantly, it enables the model to ingest multiple smaller, related blocks simultaneously, allowing it to learn not just from the content of a block but also from its surrounding context. For example, the model can learn that a text block immediately following a block labeled `Body` and preceding one labeled `Bibliography` is highly likely to also be `Body` or a section heading. This contextual understanding is a powerful signal for classification that is inaccessible to models with smaller context windows.

For the initial baseline model, the implementation should follow a standard sequence classification paradigm.19 The process for each text block provided by the `docling` tool would be as follows:

1. **Input Formulation:** The raw text content of a single document block serves as the input sequence.
2. **Tokenization:** The text is tokenized using ModernBERT's specific tokenizer.
3. **Model Forward Pass:** The tokenized sequence is passed through the ModernBERT model.
4. **Classification:** The final hidden state corresponding to the special `` token, which serves as an aggregated representation of the entire sequence, is fed into a linear classification head. This head will have a number of output neurons (logits) equal to the number of classes in the defined schema (10 in the proposed case).
5. **Prediction:** A softmax function is applied to the logits to produce a probability distribution over the classes, and the class with the highest probability is chosen as the prediction.

This text-only baseline will serve as the foundation for the iterative improvements detailed in the subsequent section.



## A Phased Roadmap for Iterative Performance Enhancement



Achieving state-of-the-art performance in document layout analysis is not a single step but an iterative process of training, evaluation, and refinement. The following phased roadmap provides a systematic approach to progressively enhance the initial multiclass ModernBERT model. Each phase introduces a more sophisticated technique designed to address specific weaknesses identified in the previous stage, building from a robust baseline toward a highly specialized and accurate final system.



### Phase 1: Rigorous Baseline Evaluation and Error Analysis



The first and most critical phase is to establish a reliable performance baseline for the initial text-only multiclass model and to conduct a deep analysis of its failure modes. This analysis will guide all subsequent optimization efforts.

**Evaluation Metrics:** It is imperative to move beyond simple accuracy, which is ill-suited for imbalanced classification tasks.9 The evaluation must focus on metrics that provide a nuanced view of the model's performance, especially concerning the target `Body` class.

- **Primary Success Metric:** The **F1-Score for the `Body` class** should be the primary metric for optimization. The F1-score, as the harmonic mean of precision and recall, provides a balanced measure of the model's ability to correctly identify `Body` text blocks without generating an excessive number of false positives or false negatives.11
- **Secondary Diagnostic Metrics:** To gain a comprehensive understanding of the model's overall health, the following should also be tracked:
  - **Per-Class Precision and Recall:** Calculating these for all 10 classes will reveal which specific document elements the model struggles to identify.12
  - **Macro-Averaged F1-Score:** This metric calculates the F1-score for each class independently and then averages them, giving equal weight to each class regardless of its frequency. It is a strong indicator of how well the model performs across all classes, including rare ones.12
  - **Balanced Accuracy:** This is the average of recall obtained for each class and provides a fair measure of accuracy on imbalanced datasets.13

**The Confusion Matrix as a Diagnostic Tool:** The confusion matrix is the single most valuable artifact for qualitative error analysis.9 It provides a detailed breakdown of misclassifications, revealing systematic patterns of confusion between classes. The analysis should focus on identifying the most frequent and problematic error types related to the `Body` class. For example:

- **`Body` -> `Footnote` Errors:** A high number of instances in this cell might indicate that the model struggles with the transition from main text to footnotes at the bottom of a page, or that it is confused by `Body` text that contains in-line citations.
- **`Body` -> `Abstract` Errors:** Confusion here could point to semantic similarities between the introductory paragraphs of the main body and the abstract, suggesting that purely textual features are insufficient to distinguish them reliably.
- **`Footnote` -> `Body` Errors:** This type of error would directly impact the purity of the extracted `Body` text and must be minimized. It might occur if footnotes are long and contain prose-like sentences.

**Qualitative Error Analysis:** Beyond the quantitative analysis of the confusion matrix, it is essential to perform a manual, qualitative review of a sample of misclassified text blocks. This process involves examining the actual text and its context within the original PDF to understand *why* the model failed. Are the misclassified `Body` blocks consistently short paragraphs at the end of a section? Do they appear in a different column layout? Do they contain unusual formatting? This deep-dive analysis generates critical hypotheses that will inform the strategies employed in the subsequent phases of improvement.35



### Phase 2: Mitigating Class Imbalance and Hard-to-Classify Examples



The analysis from Phase 1 will likely reveal two common issues: poor performance on minority classes due to data imbalance, and persistent confusion between classes that share similar features. Standard cross-entropy loss is suboptimal in these scenarios because it treats every class and every training example with equal importance. This phase introduces two powerful techniques to refine the loss function, compelling the model to focus its learning on the most challenging aspects of the classification task.

The underlying rationale is that not all errors are created equal. An error on a rare class like `Abstract` should be penalized more heavily than an error on a common class like `Body` to ensure the model learns to recognize all document elements. Similarly, an error on a "hard" example (e.g., a short, citation-heavy `Body` paragraph that is easily mistaken for a `Footnote`) is more informative for learning a robust decision boundary than an error on an "easy" example (e.g., a long, dense paragraph of prose).

**Actionable Steps:**

- **A. Class Weighting:** The first and most direct method to address class imbalance is to introduce class weights into the loss function. This technique modifies the standard `CrossEntropyLoss` by assigning a higher penalty to misclassifications of instances from minority classes and a lower penalty to those from majority classes.37 The weights are typically calculated to be inversely proportional to the class frequencies in the training data.37 For example, if the `Abstract` class appears 100 times less frequently than the `Body` class, a misclassification of an `Abstract` block would contribute significantly more to the total loss, forcing the model to prioritize learning its features. Most deep learning frameworks, including those used by the Hugging Face `Trainer`, allow for the straightforward integration of a weight tensor into the loss function.40
- **B. Focal Loss:** As a more sophisticated and often more powerful alternative, Focal Loss addresses both class imbalance and the problem of hard versus easy examples.41 Focal Loss is a modification of the cross-entropy loss that introduces a modulating factor, ![img](data:,), where ![img](data:,) is the model's predicted probability for the correct class and ![img](data:,) is a tunable focusing parameter.42
  - **Mechanism:** For an "easy" example that the model correctly classifies with high confidence (e.g., ![img](data:,)), the modulating factor becomes very small (e.g., ![img](data:,)), effectively down-weighting this example's contribution to the total loss. For a "hard" example where the model is uncertain or incorrect (e.g., ![img](data:,)), the modulating factor is large (e.g., ![img](data:,)), amplifying its contribution to the loss.
  - **Impact:** This mechanism dynamically focuses the model's training on the most informative examples—those that lie near the decision boundary and are most likely to be misclassified.43 This is particularly effective for refining the boundaries between confusing classes like `Body` and `Footnote`. Implementing Focal Loss typically requires subclassing the Hugging Face `Trainer` to override the `compute_loss` method, allowing for the substitution of the standard loss function with a custom Focal Loss implementation.45



### Phase 3: Integrating Spatial Intelligence



While the previous phases focus on optimizing the learning process based on textual content, this phase introduces a transformative new modality of information: spatial layout. Document layout analysis is fundamentally a multimodal problem. The identity of a structural element like a `Header`, `Footer`, or `Footnote` is often defined more by its geometric position and dimensions on the page than by its textual content alone. By relying solely on text, the model is being asked to solve a geometric problem with semantic tools, which is an inefficient approach that inherently limits its maximum achievable performance.

The `docling` tool provides the bounding box coordinates (`x0`, `y0`, `x1`, `y1`) for each extracted text block. This geometric data is a rich, untapped source of information that can provide powerful discriminative signals to the model. State-of-the-art document AI models, such as LayoutLMv3 and the recently proposed Spatial ModernBERT, owe their success precisely to their ability to fuse textual and spatial embeddings into a unified representation.47

**Actionable Steps:**

- **A. Simple Feature Engineering:** A direct and effective method for incorporating spatial information is to engineer discrete features from the bounding box coordinates and prepend them to the text sequence as special tokens. The process would be:

  1. Normalize all bounding box coordinates to a range of $$ based on the page dimensions.

  2. Calculate the block's relative width and height.

  3. Discretize these continuous values into a fixed vocabulary (e.g., quantize them into 100 bins from 0 to 99).

  4. Create special tokens for each possible value (e.g., `<X0_15>`, `<Y0_85>`, `<W_80>`, `<H_10>`).

  5. Prepend these special tokens to the text input: <X0_15> <Y0_85> <W_80> <H_10> The actual text of the block...

     This approach allows the transformer's self-attention mechanism to directly learn correlations between a block's position/size and its class label, without requiring architectural changes.

- **B. Architectural Integration (Spatial Embeddings):** For maximum impact, a more advanced approach inspired by models like Spatial ModernBERT and LayoutLMv3 should be adopted.47 This involves creating a dedicated spatial embedding vector that is combined with the model's standard text embeddings.

  1. **Create Spatial Embeddings:** For each token in the input sequence, obtain its bounding box coordinates. (For this token classification setup, all tokens within a single block would share the same block-level coordinates).

  2. **Embed Coordinates:** As described in the Spatial ModernBERT architecture, embed each of the four coordinates (`xmin`, `ymin`, `xmax`, `ymax`) and the two derived dimensions (`width`, `height`) into separate, high-dimensional vectors (e.g., 128 dimensions each). Concatenate these to form a rich spatial embedding vector (e.g., a 768-dimensional vector).47

  3. Fuse Embeddings: Add this spatial embedding vector to the corresponding token's word and positional embeddings before the sequence is fed into the first layer of the ModernBERT encoder.

     This architectural modification provides the model with a continuous, high-dimensional representation of layout information at every layer, enabling a much deeper and more nuanced fusion of textual and geometric context. This step is predicted to yield the most significant leap in performance, particularly in resolving ambiguities between classes that are position-dependent, such as Body, Footnote, and Header.



### Phase 4: Schema Refinement and Advanced Hybrid Models



After integrating spatial intelligence, the model's performance will be significantly higher. This final phase focuses on advanced refinements based on the new error profile of the spatially-aware model and considers a sophisticated hybrid architecture to maximize precision and recall for the `body` class.

**Schema Refinement:** The confusion matrix from the Phase 3 model should be re-analyzed. At this stage, any remaining systematic confusion between classes may indicate a flaw in the class schema itself.

- **Merging Classes:** If two classes remain highly confused even with spatial information (e.g., the model still struggles to differentiate `Table` from `Figure`), it may be pragmatic to merge them into a single, more general class (e.g., `Table_Figure`). This simplifies the classification task for the model by removing a difficult-to-learn decision boundary that may not be critical for the primary goal.
- **Splitting Classes:** Conversely, if a single class exhibits high internal variance and is a source of errors (e.g., `Body` blocks are frequently confused with long `Block_Quote` sections that are technically part of the body but have distinct formatting), it may be beneficial to split the class. Creating separate `Body_Paragraph` and `Body_Quote` classes could allow the model to learn a more precise definition for standard prose, thereby improving the purity of the final `Body` extraction. This should only be done if sufficient training examples exist for the new, more granular classes.

**The Hybrid Model:** To achieve the highest possible performance on the `Body` class, a two-stage hybrid pipeline can be implemented. This approach combines the strengths of the multiclass model's broad categorization with the focused power of a specialized binary classifier.4

1. **Stage 1 (Multiclass Segmenter):** The best-performing multiclass model from Phase 3 is used as a powerful "coarse-grained segmenter" or "noise filter." Its purpose is to process the entire document and assign an initial label to every text block. This stage will effectively and with high confidence identify and remove the vast majority of clear non-body elements, such as `Headers`, `Footers`, `Bibliography`, and most `Footnotes`.
2. **Stage 2 (Binary Refiner):** A new, highly specialized binary classification model is trained. This model's task is not to classify all text blocks, but only to operate on a small, ambiguous subset of the data. Specifically, it is trained to distinguish between the `Body` class and only those one or two classes that it was most frequently confused with in Stage 1 (e.g., `Footnote` and `Abstract`). The input to this model would be all text blocks that the Stage 1 model classified as `Body`, `Footnote`, or `Abstract`. By focusing on this narrow, highly challenging decision boundary, the binary refiner can dedicate its entire capacity to learning the subtle features that separate these confusing classes, without being distracted by the easily classifiable elements.

This two-stage approach leverages the multiclass model for its superior representation learning and ability to structure the problem, while deploying a targeted binary model for its precision in resolving the most difficult boundary cases, ultimately leading to a system with exceptionally high precision and recall for the `Body` class.



## Conclusion and Strategic Recommendations



The task of accurately extracting `body` text from the highly structured domain of legal scholarship documents is a sophisticated challenge that benefits immensely from a carefully considered classification strategy. The analysis presented in this report demonstrates that the choice between a binary and a multiclass framework is not merely a matter of implementation detail but a fundamental architectural decision that dictates the model's learning capacity and ultimate performance.



### Summary of Findings



The investigation yields several key conclusions that should guide the development process:

- **Multiclass Superiority:** For document layout analysis in a domain with regular, recurring structural elements, a multiclass training approach is unequivocally superior to a binary (`body` vs. `not-body`) approach. The multiclass framework compels the model to learn a rich, discriminative set of features for each document component by partitioning the feature space. This process of learning to distinguish between all classes (e.g., `footnote` vs. `header`) has the direct and powerful side effect of creating a more robust and well-defined representation for the target `body` class.
- **The Importance of Iteration:** Achieving state-of-the-art performance is an iterative journey. A phased roadmap—beginning with a strong multiclass baseline, systematically analyzing its errors, addressing class imbalance and hard examples through advanced loss functions, integrating spatial features, and finally refining the architecture—provides the most reliable path to success.
- **The Critical Role of Spatial Information:** The integration of spatial information derived from bounding box coordinates is not an optional refinement but a critical and transformative step. Document layout is inherently a geometric problem, and providing the model with explicit spatial features is essential to unlock the highest levels of accuracy, particularly for resolving ambiguities that are position-dependent.



### Prioritized Checklist for Implementation



The following prioritized checklist provides a clear, actionable plan for implementing the strategies outlined in this report:

1. **Commit to a Multiclass Foundation:** Formally adopt the multiclass strategy as the foundational approach for the project. Avoid the binary framework to prevent encountering the "garbage can" problem and to build on a stronger theoretical footing from the start.
2. **Define and Implement the Class Schema:** Implement the proposed 10-class schema (`Title`, `Author_Affiliation`, `Abstract`, `Body`, `Footnote`, `Header`, `Footer`, `Bibliography`, `Table_Figure`, `Equation`) during the data annotation phase. This schema is optimized for the structure of legal scholarship documents.
3. **Train and Evaluate the Text-Only Baseline:** Fine-tune a standard ModernBERT D1024 model using only the text content of the document blocks. Establish a rigorous performance baseline using the F1-Score for the `Body` class as the primary metric, supplemented by a full confusion matrix and per-class precision/recall metrics.
4. **Conduct Deep Error Analysis:** Perform a thorough quantitative and qualitative analysis of the baseline model's errors. Identify the most common types of misclassifications involving the `Body` class and form hypotheses about their root causes.
5. **Apply Imbalance and Hard-Example Techniques:** Iterate on the baseline model by first introducing class weights into the loss function to counteract data imbalance. Subsequently, experiment with implementing Focal Loss to compel the model to focus on the most challenging classification examples identified during error analysis.
6. **Integrate Spatial Features:** This is the highest-impact step. Augment the model's input to include spatial information from the text blocks' bounding box coordinates. Begin with simple feature engineering (prepending special tokens) and progress to a full architectural integration by creating and fusing dedicated spatial embeddings with the text embeddings.
7. **Evaluate, Refine, and Finalize:** Re-evaluate the performance of the spatially-aware model. Use the new error profile to make final refinements to the class schema if necessary (merging or splitting classes). For maximum performance, consider implementing the two-stage hybrid model, using the multiclass model as a primary segmenter and a specialized binary model to refine the most ambiguous cases.
