## Dependence-Aware Label Aggregation for LLM-as-a-Judge via Ising Models

1 , 2 2

Krishnakumar Balasubramanian , Aleksandr Podkopaev , Shiva Prasad Kasiviswanathan 2 1 Department of Statistics, University of California, Davis 2 Amazon Web Services

February 2, 2026

## Abstract

Large-scale AI evaluation increasingly relies on aggregating binary judgments from K annotators, including LLMs used as judges. Most classical methods, e.g., Dawid-Skene or (weighted) majority voting, assume annotators are conditionally independent given the true label Y ∈ { 0 , 1 } , an assumption often violated by LLM judges due to shared data, architectures, prompts, and failure modes. Ignoring such dependencies can yield miscalibrated posteriors and even confidently incorrect predictions. We study label aggregation through a hierarchy of dependenceaware models based on Ising graphical models and latent factors. For class-dependent Ising models, the Bayes log-odds is generally quadratic in votes; for class-independent couplings, it reduces to a linear weighted vote with correlation-adjusted parameters. We present finiteK examples showing that methods based on conditional independence can flip the Bayes label despite matching per-annotator marginals. We prove separation results demonstrating that these methods remain strictly suboptimal as the number of judges grows, incurring nonvanishing excess risk under latent factors. Finally, we evaluate the proposed method on three real-world datasets, demonstrating improved performance over the classical baselines.

## 1 Introduction

Large-scale evaluation of modern AI systems increasingly relies on aggregating binary judgments from multiple annotators that are predominantly LLMs used as judges. Given an item with unknown label Y ∈ { 0 , 1 } and K noisy votes J = ( J 1 , . . . , J K ) ∈ { 0 , 1 } K , the core statistical problem is to infer Y from J . Many classical aggregators such as majority vote, weighted majority vote, and Dawid-Skene (DS) [12] estimators are built around the conditional independence (CI) assumption: they treat annotators as independent voters given Y , i.e., P( J | Y ) = ∏ K j =1 P( J j | Y ). Under this assumption, the weighted majority vote estimator is Bayes-optimal, and the DS estimator provides a practical approach for estimating the weights using the popular Expectation-Maximization algorithm, subject to appropriate identifiability conditions.

The CI assumption is however increasingly mismatched to contemporary evaluation pipelines, especially for LLM judges, where correlations arise from shared pretraining corpora, architectures, prompts, and failure modes [18, 24, 41]. Dependence is not a benign nuisance: it can fundamentally change the information content of the votes. When judges are redundant or co-vary, aggregation approaches based on the CI assumption (which we refer to as CI-predictors and which are typically based on weighted majority voting) can over-count agreement and yield systematically miscalibrated predictions. In Appendix B, we demonstrate this through a three-annotator example: when

<!-- image -->

̸

Figure 1: Graphical models for LLM-as-a-judge. Conditional independence (CI); (left) : judges are independent given Y (represented by lack arrows connecting the Judge LLMs). Class-dependent Ising; (right) : judges exhibit pairwise dependence whose pattern can change with the label ( W (0) = W (1) ), enabling class information to affect directly the correlations among judges.

the dependence is captured via an Ising model explained shortly, the posterior prediction for the labels (assuming CI) predicts the opposite label with near-certainty, even given correct per-annotator marginals. This illustrates a key insight: misspecified dependence structure can dominate correct marginal modeling.

In this work, we revisit label aggregation through the lens of Ising graphical models 1 , i.e., quadratic Markov random fields of the form

<!-- formula-not-decoded -->

for J ∈ { 0 , 1 } K , y ∈ { 0 , 1 } ; see Figure 1 for a graphical model illustration. Here h ( y ) ∈ R K is a vector of classy local fields capturing per-judge bias/strength: h ( y ) j controls how likely judge j is to output 1 under class y (holding other votes fixed). The symmetric matrix W ( y ) ∈ R K × K (with zero diagonal) is the classy coupling matrix encoding pairwise dependencies: W ( y ) jk > 0 encourages judges j and k to co-vote 1, while W ( y ) jk < 0 discourages co-voting and captures antagonistic or compensatory behavior. In LLM-as-a-judge settings, h ( y ) reflects each judge's label-conditional tendency to vote for class 1, while W ( y ) represents persistent agreement/disagreement patterns induced by shared, training data, architectures, and failure modes.

̸

Building on this representation, we introduce the model hierarchy in Figure 2. The most expressive model is the class-dependent Ising model , which allows class-specific interactions ( W (0) = W (1) ) and yields Bayes log-odds that are generally quadratic in the votes. An important special case is the class-independent Ising model where couplings are shared across classes ( W (0) = W (1) ): in this case, the quadratic terms cancel in the likelihood ratio and the Bayes log-odds reduce to a linear weighted vote in J . Importantly, dependence still matters-correlations are absorbed into correlation-corrected weights and intercepts-allowing this model to discount redundant agreement while retaining the simplicity of a linear aggregation rule.

## 1.1 Our Contributions

- Dependence-aware Model Hierarchy. In Section 2, we formalize the model hierarchy spanning CI model, class-independent Ising model (shared interactions), and class-dependent Ising model (class-specific interactions). Wederive the exact Bayes log-odds for class-dependent

1 We note that the multiclass setting can be handled by working with Potts models [36].

̸

<!-- image -->

Conditional Independence (CI)

Bayes-optimal: (weighted) linear aggregation

Figure 2: Model hierarchy via set inclusion: Conditional Independence (CI) ⊂ Class-independent Ising ⊂ Class-dependent Ising.

Ising model which is quadratic in votes, and show that under class-independent Ising model, the Bayes rule reduces to a linear weighted vote with dependence-adjusted parameters.

- Separation Results. In Section 3, we establish a sharp separation result under the classdependent Ising model. We show that there exist regimes where each judge is better than random, yet the CI-predictor still makes a constant fraction of errors by misinterpreting correlated 'wrong-mode' agreement as strong evidence. In contrast, the Bayes-optimal predictor exploits the dependence structure and achieves vanishing error as the number of judges grows, creating non-vanishing risk separation between the two methods.
- Relation to Factor Models. In the crowdsourcing literature, another way to model judge dependence is via latent-factor model with a shared random effect Z (independent of Y ) such that judges are conditionally independent only given ( Y, Z ): P( J | Y, Z ) = ∏ K j =1 P( J j | Y, Z ) [42, 43]. We show that the CI-predictor which ignores Z can remain strictly suboptimal when data are generated from such factor model, even as K → ∞ . For weak coupling, we show that latent-factor models induce an approximately low-rank Ising structure, placing them between CI and class-dependent Ising model. The details are deferred to Appendix C.3.
- Experimental Validation. We evaluate the proposed aggregation method on three realworld tasks: relevance, toxicity, and summarization evaluations, using six judge models: Claude Sonnet 4.5, Claude Haiku 4.5, OpenAI gpt-oss-120b, Llama 4 Maverick 17B Instruct, Llama 4 Scout 17B Instruct, and DeepSeek-R1. In Appendix F, we include synthetic simulations that illustrate our theoretical separation results.

We defer a discussion placing our work in the context the larger literature on LLM-as-a-judge, unsupervised label aggregation and crowdsourcing to Appendix A.

## 2 Dependent LLMs-as-a-Judge Models

Suppose that we observe n independent items. Item i has an unobserved label Y i ∈ { 0 , 1 } , with prior P( Y i = 1) = π ∈ (0 , 1), and is annotated by K judges producing a binary vote vector J i =

( J i 1 , . . . , J iK ) ∈ { 0 , 1 } K . We assume items are independent and model within-item dependencies among judges via Ising (pairwise MRF) distribution conditional on the label: P( { J i , Y i } n i =1 ) = ∏ n i =1 P( Y i ) P( J i | Y i ). This makes the label inference problem for each item separable given model parameters 2 .

̸

In LLM-as-a-judge pipelines, the within-item dependencies arise due to shared pretraining data, architectures, and prompt templates (leading to label-independent redundancy and shared failure modes), while in other settings dependence itself can be label-dependent (e.g., certain classes trigger common hallucination patterns or refusal behaviors), motivating two practically distinct regimes: a class-dependent structure W (0) = W (1) that allows correlation patterns to change with the true label and a class-independent interaction structure W (0) = W (1) that captures persistent correlations across all items.

## 2.1 Class-dependent Ising Model

In the most general form, the class-conditional distribution of the K votes is allowed to differ across labels: for each y ∈ { 0 , 1 } , we have

̸

<!-- formula-not-decoded -->

where h ( y ) ∈ R K are classy local fields (biases), W ( y ) ∈ R K × K is a symmetric coupling matrix with zero diagonal, and Z ( y ) is the corresponding partition function. This model captures the possibility that judges are correlated even after conditioning on the label where the strength/pattern of correlation may itself depend on the class.

Bayes-optimal Posterior. For a single item, we write J = ( J 1 , . . . , J K ). The Bayes' rule gives posterior log-odds:

̸

<!-- formula-not-decoded -->

where ∆ h j := h (1) j -h (0) j , ∆ W jk := W (1) jk -W (0) jk and ∆ Z := -log Z (1) + log Z (0) . The term ∆ Z is constant in J (for fixed parameters and fixed K ) and can be absorbed into the intercept. Since W ( y ) is symmetric with zero diagonal, one can equivalently rewrite the quadratic term as 1 2 ∑ j = k ∆ W jk J j J k = ∑ 1 ≤ j\<k ≤ K ∆ W jk J j J k . Therefore, the Bayes-optimal predictor takes form:

<!-- formula-not-decoded -->

̸

where a j = ∆ h j , b jk = ∆ W jk and b 0 = log π 1 -π +∆ Z . When W (1) = W (0) , the optimal decision boundary is quadratic in the votes since class information may be present not only in marginal accuracies (fields) but also in label-dependent correlation structure (couplings).

2 The literature on Ising models use spins: ± 1. Our inference algorithm is unchanged under the bijection X ij = 2 J ij -1; we keep Y, J ∈ { 0 , 1 } throughout for consistency.

̸

## 2.2 Class-Independent Couplings

A common and interpretable special case is one in which the dependence structure among judges is shared across both classes but individual biases and accuracies shift with the label. Specifically, we assume

̸

<!-- formula-not-decoded -->

where h j represents a label-independent baseline field, c j controls how the label shifts judge j 's field, and W is a shared symmetric coupling matrix (with zero diagonal). Here, the normalizer Z ( y ) may still depend on y since the fields differ across classes.

Bayes-optimal Posterior. Under (3), the posterior log-odds simplify substantially:

<!-- formula-not-decoded -->

where ∆ Z = -log Z (1) +log Z (0) is a constant in J . The quadratic terms cancel since the coupling matrix is shared across the two classes. Therefore, the Bayes-optimal predictor is a linear threshold rule:

<!-- formula-not-decoded -->

If one prefers ± 1 labels instead of { 0 , 1 } , one can define centered spins X j := 2 J j -1 ∈ {± 1 } . Then ∑ j c j J j = 1 2 ∑ j c j X j + 1 2 ∑ j c j , so the rule remains a weighted vote on X after absorbing 1 2 ∑ j c j into the intercept. If W ≡ 0, then the judges are conditionally independent given Y and (3) reduces to a product of Bernoulli marginals: P( J | Y = y ) = ∏ K j =1 P( J j | Y = y ) with P( J j = 1 | Y = y ) = σ ( h j + ( y -1 2 ) c j ) , where σ ( t ) = (1 + e -t ) -1 . In this case, the per-judge contribution to the posterior log-odds can be written as an affine function of J j :

<!-- formula-not-decoded -->

̸

where p ( y ) j := P( J j = 1 | Y = y ). Summing over j recovers the classical CI or Naive-Bayes linear aggregation rule with weights equal to differences of logits; in the parameterization (3), logit( p (1) j ) -logit( p (0) j ) = c j . When W = 0 but is shared across classes , correlations do not introduce quadratic terms into the Bayes log-odds (they cancel in (4)), and the Bayes decision remains linear in J . Nevertheless, correlations still matter statistically: they change the joint law of J within each class and therefore affect likelihoods, partition functions (hence the intercept b 0 ), and parameter estimation from finite data. In contrast, if the couplings differ across classes ( W (1) = W (0) ), then class information is present in the dependence structure and the Bayes decision becomes quadratic as in (2).

̸

For the sake of completeness, we discuss the CI model with asymmetric errors (which leads to weighted majority vote aggregators) in Appendix C.1. We also briefly discuss the similarities and differences with the linear and quadratic discriminant analysis model, that are standard Gaussian models (as opposed to the binary Ising models) in Appendix C.2.

## 3 Separation Results

In this section, we use our model hierarchy to clarify when standard aggregation rules are justified for LLM-as-a-judge pipelines and when those fail. Weighted majority vote (with sufficiently accurate weights) is Bayes-optimal under conditional independence (CI) Ai et al. [2, Theorem 1]. However, as argued in the introduction and illustrated by our motivating examples (Appendix B), satisfying CI is often implausible for LLM judges due to shared pretraining corpora, similar architectures, reused prompt templates, and common safety/refusal or hallucination failure modes. These dependencies are not merely noise: they can encode item properties (e.g., difficulty or trigger patterns) and the redundancy of evidence across judges.

We show a separation (in terms of risk) between majority voting procedures and the Bayesoptimal predictor under two dependence mechanisms relevant to LLM-as-a-judge: (a) shared latent factors inducing low-rank correlations (Appendix C.3.1) and (b) interaction-driven dependence captured by the Curie-Weiss model, a special case of the Ising model, with strong agreement modes (Section 3.1). These separation results clearly demonstrate the limitations in expressive power of schemes such as majority voting. The proofs are deferred to Appendix E.

## 3.1 Sub-optimality of CI-predictor under Ising Dependence

The risk of a binary aggregator g in our setting is defined as R ( g ) := P( g ( J ) = Y ). We start by establishing a separation result in terms of risk between a special case of Ising model, namely the Curie-Weiss model, which has been widely used in opinion dynamics [5]. Informally, we show that even with infinitely many judges, any CI-predictor remains strictly suboptimal, whereas there exists a Bayes predictor that leverages dependence (quadratic structure) to classify essentially perfectly.

̸

Theorem 1 (Nonvanishing Bayes vs. CI Separation for Class-conditional Ising Models) . Fix a prior P( Y = 1) = π ∈ (0 , 1) . For each K ≥ 1 , let J = ( J 1 , . . . , J K ) ∈ { 0 , 1 } K denote the K judges' votes for a single item and define the recoded spins X j := 2 J j -1 ∈ {-1 , +1 } and let M K := 1 K ∑ K j =1 X j ∈ { -1 , -1 + 2 K , . . . , 1 } . Assume the following class-conditional Curie-Weiss Ising model: there exist constants 0 < β 0 < 1 < β 1 such that, conditional on Y = y ∈ { 0 , 1 } ,

<!-- formula-not-decoded -->

̸

for x ∈ {-1 , +1 } K . Equivalently (writing x j = 2 j j -1 ), this is a special case of the { 0 , 1 } -Ising form (1) with h ( y ) j = -2 β y ( 1 -1 K ) and W ( y ) jk = 4 β y K ( j = k ) , up to an additive constant absorbed into Z ( y ) .

Let g ⋆ K be the Bayes-optimal predictor under the true model (6) . Let g ind K be the population CI-predictor that replaces the true joint by the product of true one-dimensional marginals, i.e., P ind ( J = j | Y = y ) := ∏ K r =1 q j r y (1 -q y ) 1 -j r with q y := P( J r = 1 | Y = y ) ( independent of r ) , and then thresholds the induced posterior P ind ( Y = 1 | J ) at 1 / 2 . Then the following results hold:

1. (CI Collapses to the Prior) For every K and y ∈ { 0 , 1 } , one has q y = 1 2 . Consequently, P ind ( Y = 1 | J ) = π for all J , so g ind K ( J ) ≡ 1 { π ≥ 1 2 } , and R ( g ind K ) = min { π, 1 -π } , ∀ K .
1. (Bayes Risk Vanishes) Let m ⋆ = m ⋆ ( β 1 ) ∈ (0 , 1) denote the unique positive solution to

m = tanh( β 1 m ) . Then for any fixed threshold t ∈ (0 , m 2 ⋆ ) , the quadratic statistic test:

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

satisfies R (˜ g K ) → 0 as K →∞ . Hence R ( g ⋆ K ) → 0 as K →∞ .

## 3. (Nonvanishing Separation) We have:

<!-- formula-not-decoded -->

Theorem 1 gives a clean population-level separation between the Bayes-optimal predictor and a CI-predictor when the judges are dependent given the label. We consider a setting where, for each label y ∈ { 0 , 1 } , the K votes are drawn from a class-conditional Ising model. In the particular Curie-Weiss specialization used in the theorem, the conditional law depends only on the global magnetization M K and the dependence strength differs across classes: the negative class is in a high-temperature regime ( β 0 < 1), while the positive class is in a low-temperature regime ( β 1 > 1).

In this model the two classes have the same one-dimensional marginals: for every judge j and both labels y ∈ { 0 , 1 } , P( J j = 1 | Y = y ) = 1 / 2 . Thus, looking at each judge in isolation provides no information about the label. The only distinguishing signal is in the dependence structure : under Y = 1 the votes exhibit strong global alignment (many judges tend to agree), whereas under Y = 0 they do not. The CI-predictor replaces the true joint likelihood by a product of these one-dimensional marginals. Since the marginals are identical across classes, under CI, the likelihood ratio is identically 1, so the posterior stays equal to the prior π for every vote vector J . Consequently, the CI-predictor ignores the data entirely and achieves risk R ( g ind K ) = min { π, 1 -π } , independently of K .

In contrast, the Bayes-optimal posterior uses the correct class-conditional joint likelihood, which depends on quadratic (pairwise) interactions among votes and, in this Curie-Weiss case, can be expressed through the statistic M 2 K . As K grows, the magnetization concentrates at 0 under the high-temperature class ( Y = 0) and concentrates near a nonzero value under the low-temperature class ( Y = 1) (up to a random global sign flip). Therefore, a simple quadratic rule such as 1 { M 2 K ≥ t } (for any fixed t between 0 and the squared limiting magnetization under Y = 1) separates the two classes with vanishing error as K →∞ . Since the Bayes rule is optimal, its risk also converges to 0. Putting the two pieces together, the Bayes-optimal risk goes to zero while the CI risk stays bounded away from zero.

## 3.2 Extension to Informative Marginals

The Curie-Weiss separation example in Theorem 1 uses the zero-field Curie-Weiss model, which is invariant under the global flip X ↦→-X . This symmetry forces q 0 = q 1 = P( J j = 1 | Y = y ) = 1 2 for both classes, so a CI-predictor that only uses one-dimensional marginals collapses to the prior. While this may look like a 'corner case,' the underlying failure mechanism is not : the CI-predictor cannot exploit class information carried by dependence structure (correlation/interaction patterns), and this can remain true even when individual marginals are (slightly) informative.

At a basic level, risks vary continuously with the data-generating law: if P and Q are two joint distributions on ( Y, J ) and d TV ( P, Q ) := sup A | P ( A ) -Q ( A ) | is their total variation distance, then for any classifier g , | R P ( g ) -R Q ( g ) | ≤ d TV ( P, Q ), and in particular we have | R ⋆ P -R ⋆ Q | ≤ d TV ( P, Q ),

<!-- formula-not-decoded -->

̸

because R P ( g ) = P ( g ( J ) = Y ) is the probability of a measurable event, where R ⋆ P is Bayes-optimal risk under distribution P . Thus, for any fixed (moderate) K , the large finite-sample gaps exhibited by the symmetric Curie-Weiss example persist under small perturbations of the class-conditional distributions, including perturbations that move the marginals away from 1 / 2.

The next result gives an explicit asymptotic variant in which each judge is individually better than random ( q 0 < 1 / 2 < q 1 ), yet the CI risk remains bounded away from zero while the Bayesoptimal risk still vanishes as K → ∞ . The key idea is to retain phase coexistence in the lowtemperature class so that, with constant probability, the judges collectively enter a 'wrong-sign' agreement mode that a CI-predictor interprets as decisive evidence for the wrong label, whereas the Bayes-optimal predictor uses a dependence-sensitive statistic (here | M K | ) to identify the true class.

Theorem 2 (Curie-Weiss separation with informative marginals) . Let Y ∈ { 0 , 1 } with P( Y = 1) = π ∈ (0 , 1) . For each K ≥ 1 , define spins X = ( X 1 , . . . , X K ) ∈ {-1 , +1 } K and votes J j = ( X j +1) / 2 ∈ { 0 , 1 } . Let the class-conditional laws of X be Curie-Weiss models with (possibly K -dependent) external fields:

<!-- formula-not-decoded -->

for y ∈ { 0 , 1 } . Assume parameters satisfy:

1. (High-temperature Class) β 0 ∈ (0 , 1) and h 0 ,K ≡ h 0 < 0 is a fixed negative constant;
1. (Low-temperature Class with Weak Symmetry Breaking) β 1 > 1 and h 1 ,K = c/K with some fixed c > 0 .

Let M K := 1 K ∑ K j =1 X j ∈ [ -1 , 1] be the magnetization. Let m 0 ∈ ( -1 , 0) be the unique solution of the mean-field equation m 0 = tanh( β 0 m 0 + h 0 ) , and let m ⋆ = m ⋆ ( β 1 ) ∈ (0 , 1) be the unique positive solution of m ⋆ = tanh( β 1 m ⋆ ) . Define

<!-- formula-not-decoded -->

Assume additionally that

<!-- formula-not-decoded -->

Let g ⋆ K denote the Bayes predictor under the true model (7) . Let g ind K denote the population CIpredictor that replaces P( J | Y = y ) by the product of the true marginals ∏ K j =1 q J j y (1 -q y ) 1 -J j .Then, the following hold:

1. (Informative Marginals) Each judge is individually better than random: q 0 < 1 2 < q 1 (equivalently, specificity 1 -q 0 > 1 2 and sensitivity q 1 > 1 2 ).
1. (Bayes Risk Vanishes) For any fixed threshold t satisfying | m 0 | < t < m ⋆ , the aggregator ˜ g K ( J ) := 1 {| M K | ≥ t } has R (˜ g K ) → 0 as K →∞ . Consequently, R ( g ⋆ K ) → 0 .

Table 1: Test accuracy for the various methods on the three datasets. Numbers are averages over 20 trials. CI-WMV and CI-UMV correspond to weighted and uniform majority vote both of which operator under conditional independence assumptions. Class-Dep. and Class-Indep. refer to classdependent and class-independent Ising models, respectively.

| Dataset | Class-Dep. Ising (ours) | Class-Indep. Ising (ours) | CI-WMV | CI-UMV |
|---------------|---------------------------|-----------------------------|----------|----------|
| Relevance | 0.9 | 0.88 | 0.82 | 0.8 |
| Toxicity | 0.79 | 0.77 | 0.72 | 0.69 |
| Summarization | 0.68 | 0.64 | 0.61 | 0.6 |

3. (CI Remains Bounded away from Bayes) As K →∞ , we have R ( g ind K ) → π (1 -p ) , and hence lim K →∞ ( R ( g ind K ) -R ( g ⋆ K ) ) ≥ π (1 -p ) > 0 .

Remark 1 (Continuity viewpoint) . In Theorem 2, the limiting CI error is π (1 -p ) with p = σ (2 cm ⋆ ) , which varies continuously with the 'weak symmetry-breaking' strength c . As c ↓ 0 , one has p → 1 / 2 and q 1 ↓ 1 / 2 , recovering the symmetric example; for any c > 0 , the marginals become informative ( q 1 > 1 2 ) yet CI still makes errors on a constant fraction (1 -p ) of the positive-class items because it thresholds the sign of the vote proportion, whereas Bayes exploits the dependenceinduced structure (here, large | M K | regardless of sign). Thus the separation is robust: it is driven by a persistent correlated 'wrong-sign' mode, not by the exact equality q y = 1 / 2 .

The separation results in this section are interesting for two reasons. First, they show that the limitations with the CI assumption are structural , not a finite-judge artifact: even as K →∞ , the CI-predictor remain strictly suboptimal because it cannot exploit dependence-induced information or distinguish redundant agreement from independent evidence (Ising interactions). Second, they explain why LLM ensembles can become overconfident for the wrong reasons: if judges share a failure mode, their agreement should be discounted rather than counted multiple times, which CI weighting cannot do. Practically, this suggests evaluation pipelines should not rely solely on per-judge accuracies or majority counts, but should monitor and model dependence among judges (e.g., residual correlations after accounting for label uncertainty). When dependence is present, our results motivate moving up the hierarchy: from CI to various Ising models, to improve accuracy, calibration, and uncertainty for downstream decisions.

## 4 Experimental Evaluation

For all experimental results, we use the Expectation-Maximization algorithm for posterior label prediction. We defer the details to Appendix D. Simulation results comparing weighted (with the weights estimated by EM algorithm) and uniform majority voting are provided in Appendix F.1. Simulation results regarding CI-predictor and factor/Ising model predictors are provided in Appendix F. Below, we provide experiments on real-world datasets.

## 4.1 Real World Datasets

We consider LLMaaJ label aggregation in three tasks: relevance, toxicity, and summarization assessment. We use the following models as judges: (a) Claude Sonnet 4.5, (b) Claude Haiku 4.5, (c) OpenAI gpt-oss-120b [33], (d) Llama 4 Maverick 17B Instruct, (e) Llama 4 Scout 17B Instruct, and (f) DeepSeek-R1 [13]. For all models, the temperature parameter is set to zero. The prompts used in our evaluations are deferred to Appendix G.3.

Relevance. We use the WikiQA dataset [44] to evaluate query-passage relevance classification, a task which arises in the context of retrieval-augmented generation (RAG). The dataset consists of natural language questions paired with multiple sentences extracted from Wikipedia. Each sentence is annotated with a binary label which indicates whether it correctly answers the question at hand. To construct inputs suitable for the relevance classification, we collect all the sentences associated with each question and concatenate them into a single text passage. The resulting passage is labeled relevant to the question if and only if at least one of the original sentences is labeled as a correct answer; see examples in Appendix G.1. In our evaluation, we use all available splits for the original dataset, resulting in approximately 3000 evaluation instances.

Toxicity. We use the Jigsaw Unintended Bias in Toxicity Classification dataset [1] for toxicity classification. We use comments from the private leaderboard test set, filtering for those with at least five human annotators and a minimum length of 100 characters. To ensure balanced representation across all toxicity levels, we use stratified sampling based on comment toxicity scores, i.e., the fraction of annotators who marked a comment as toxic. We randomly sample 1000 comments from each of the four toxicity score buckets: \[0 , 0 . 25), \[0 . 25 , 0 . 5), \[0 . 5 , 0 . 75), [0 . 75 , 1], and label a comment as toxic (positive class) if at least half of the annotators marked it as toxic. Additional preprocessing steps are deferred to Appendix G.2.

Summarization. We use the CNN/DailyMail news dataset [20, 37] for summarization assessment. The original dataset contains news articles along with short author-written summaries. For binary summarization assessment, we use a preprocessed variant of the dataset from Arize Phoenix summarization benchmark. This benchmark augments a subset of the original articles and summaries with synthetically generated incorrect summaries designed to resemble correct ones while containing factual inconsistencies. The dataset contains 1100 instances with approximately the same number of correct and incorrect summaries.

We conducted two experiments on those datasets: (i) studying the effect of varying the number of training samples n while keeping the number of judges fixed ( K = 6), and (ii) studying effect of varying K while keeping the number of training samples n fixed at roughly 10%-20% of the overall dataset. We compared the class-independent Ising-predictors, class-dependent Ising-predictors, and CI-predictors (specifically, the weighted majority vote procedure resulting from the asymmetric models described in Appendix C.1). For these experiments, we randomly sampled the training data and the judges and report the average test accuracy (and standard error) over 20 trials in Figure 3.

From Figure 3, we note that the two Ising predictors invariably outperform the CI-predictor once the number of training samples and the number of judges exceed a modest threshold (and in some regimes even with fewer training samples). As a summary, in Table 1, we also report the result of comparing the aforementioned procedures, along with the uniform majority voting procedure, when all six judges are used and when the maximum amount of training data is used for each dataset (i.e., 2500 samples for relevance, 3000 samples for toxicity, and 1000 samples for summarization tasks). We notice that Ising models outperform (weighted) majority voting procedures. In particular, as we have large number of training (unsupervised) samples relative to the number of model parameters, the class-dependent Ising model outperforms the class-independent Ising model, illustrating the benefit of moving up the hierarchy of proposed models.

The above experiments demonstrate the practical value of explicitly modeling judge dependence: when correlations are present, interaction-aware aggregation leverage the additional structure among the pool of judges and deliver consistently lower error than any conditional-independence weighting which is based only on marginals.

Figure 3: Effect of varying the number of training samples (left) and number of judges (right) on the test accuracy. Top, middle and bottom rows correspond respectively to Relevance, Toxicity and Summarization datasets. The standard errors are of small width, although they are plotted.

<!-- image -->

## 5 Limitations and Conclusion

While our separation results are stated in terms of the Bayes-optimal posterior under the true generative model, in practice one must rely on computational procedures such as generalized EM with approximate E-steps and surrogate M-steps, e.g., pseudo-likelihood. A key next step is to extend the theory from the population Bayes rule to these algorithms: establishing conditions under which the learned parameters and induced posteriors converge to the correct decision rule or, at minimum, inherit the same separation from conditional-independence baselines.

Beyond parameter estimation, our framework motivates a hypothesis-testing view of LLM-as-ajudge evaluation: before fitting more expressive dependence models, practitioners can test whether class-conditional independence is plausible by checking for residual correlations among judges after accounting for label uncertainty, or by comparing CI and Ising/factor-model pseudo-likelihoods on holdout items.

From a practical standpoint, the hierarchy presented in this paper provides actionable guidance:

one may start with CI as a cheap baseline and then move to latent-factor (low-rank) dependence if correlations appear global or prompt-driven. When pairwise agreement patterns are strong or class-dependent, one may escalate to class-independent or class-dependent Ising model. Simple diagnostics-estimated coupling strength, stability across random initializations, and predictive calibration on small labeled validation sets-can help determine the appropriate level of dependence modeling and prevent overfitting. Such considerations may make dependence-aware aggregation a reliable component of real-world evaluation pipelines.

## References

- [1] CJ Adams, Daniel Borkan, Jeffrey Sorensen, Lucas Dixon, Lucy Vasserman, and nithum. Jigsaw unintended bias in toxicity classification, 2019. URL https://kaggle.com/competi tions/jigsaw-unintended-bias-in-toxicity-classification .

- [2] Rui Ai, Yuqi Pan, David Simchi-Levi, Milind Tambe, and Haifeng Xu. Beyond majority voting: LLM aggregation by leveraging higher-order information. arXiv:2510.01499 , 2025.

- [3] Anastasios N Angelopoulos, Stephen Bates, Clara Fannjiang, Michael I Jordan, and Tijana Zrnic. Prediction-powered inference. Science , 382(6671):669-674, 2023.

- [4] Anastasios N Angelopoulos, John C Duchi, and Tijana Zrnic. PPI++: Efficient predictionpowered inference. arXiv:2311.01453 , 2023.

- [5] David B Bahr and Eve Passerini. Statistical mechanics of opinion formation and collective behavior: micro-sociology. The Journal of mathematical sociology , 23(1):1-27, 1998.

- [6] Daniel Berend and Aryeh Kontorovich. A finite sample analysis of the naive Bayes classifier. J. Mach. Learn. Res. , 16(1):1519-1545, 2015.

- [7] Bhaswar B. Bhattacharya and Sumit Mukherjee. Inference in Ising models. Bernoulli , 24(1): 493-525, 2018.

- [8] Pierre Boyeau, Anastasios Nikolas Angelopoulos, Tianle Li, Nir Yosef, Jitendra Malik, and Michael I. Jordan. Autoeval done right: Using synthetic data for model evaluation. In International Conference on Machine Learning , 2025.

- [9] Yi-Chun Chen, Manuel Mueller-Frank, and Mallesh Pai. The wisdom of the crowd and higherorder beliefs. In ACM Conference on Economics and Computation , 2023.

- [10] Yiqun T Chen, Sizhu Lu, Sijia Li, Moran Guo, and Shengyi Li. Efficient inference for noisy LLM-as-a-judge evaluation. arXiv:2601.05420 , 2026.

- [11] Aida Mostafazadeh Davani, Mark D´ ıaz, and Vinodkumar Prabhakaran. Dealing with disagreements: Looking beyond the majority vote in subjective annotations. Transactions of the Association for Computational Linguistics , 10:92-110, 2022.

- [12] A. Philip Dawid and Allan M. Skene. Maximum likelihood estimation of observer error-rates using the EM algorithm. Journal of the Royal Statistical Society. Series C (Applied Statistics) , 28(1):20-28, 1979.

- [13] DeepSeek-AI. Deepseek-R1: Incentivizing reasoning capability in LLMs via reinforcement learning. arXiv:2501.12948 , 2025.

- [14] Pinar Donmez, Guy Lebanon, and Krishnakumar Balasubramanian. Unsupervised supervised learning I: Estimating classification and regression errors without labels. Journal of Machine Learning Research , 11(4), 2010.

- [15] Yann Dubois, Percy Liang, and Tatsunori Hashimoto. Length-controlled alpacaeval: A simple debiasing of automatic evaluators. In Conference on Language Modeling , 2024.

- [16] Sacha Friedli and Yvan Velenik. Statistical mechanics of lattice systems: a concrete mathematical introduction . Cambridge University Press, 2017.

- [17] Chao Gao, Yu Lu, and Dengyong Zhou. Exact exponent in optimal rates for crowdsourcing. In International Conference on Machine Learning , 2016.

- [18] Shashwat Goel, Joschka Str¨ uber, Ilze Amanda Auzina, Karuna K Chandra, Ponnurangam Kumaraguru, Douwe Kiela, Ameya Prabhu, Matthias Bethge, and Jonas Geiping. Great models think alike and this undermines AI oversight. In International Conference on Machine Learning , 2025.

- [19] Jiawei Gu, Xuhui Jiang, Zhichao Shi, Hexiang Tan, Xuehao Zhai, Chengjin Xu, Wei Li, Yinghan Shen, Shengjie Ma, Honghao Liu, et al. A survey on LLM-as-a-judge. The Innovation , 2024.

- [20] Karl Moritz Hermann, Tom´ as Kocisk´ y, Edward Grefenstette, Lasse Espeholt, Will Kay, Mustafa Suleyman, and Phil Blunsom. Teaching machines to read and comprehend. In Conference on Neural Information Processing Systems , 2015.

- [21] Holger Hoefling and Robert Tibshirani. Estimation of sparse binary pairwise Markov networks using pseudo-likelihoods. Journal of Machine Learning Research , 10(4), 2009.

- [22] Dirk Hovy, Taylor Berg-Kirkpatrick, Ashish Vaswani, and Eduard H. Hovy. Learning whom to trust with MACE. In Conference of the North American Chapter of the Association of Computational Linguistics , 2013.

- [23] Ariel Jaffe, Ethan Fetaya, Boaz Nadler, Tingting Jiang, and Yuval Kluger. Unsupervised ensemble learning with dependent classifiers. In Conference on Artificial Intelligence and Statistics , 2016.

- [24] Elliot Myunghoon Kim, Avi Garg, Kenny Peng, and Nikhil Garg. Correlated errors in large language models. In International Conference on Machine Learning , 2025.

- [25] Hyun-Chul Kim and Zoubin Ghahramani. Bayesian classifier combination. In Conference on Artificial Intelligence and Statistics , 2012.

- [26] Matth¨ aus Kleindessner and Pranjal Awasthi. Crowdsourcing with arbitrary adversaries. In International Conference on Machine Learning , pages 2708-2717, 2018.

- [27] Chungpa Lee, Thomas Zeng, Jongwon Jeong, Jy-yong Sohn, and Kangwook Lee. How to correctly report LLM-as-a-judge evaluations. arXiv:2511.21140 , 2025.

- [28] Dawei Li, Bohan Jiang, Liangjie Huang, Alimohammad Beigi, Chengshuai Zhao, Zhen Tan, Amrita Bhattacharjee, Yuxuan Jiang, Canyu Chen, Tianhao Wu, Kai Shu, Lu Cheng, and Huan Liu. From generation to judgment: Opportunities and challenges of LLM-as-a-judge. In Conference on Empirical Methods in Natural Language Processing , 2025.

- [29] Qiang Liu, Jian Peng, and Alexander T Ihler. Variational inference for crowdsourcing. Conference on Neural Information Processing Systems , 2012.

- [30] Yang Liu, Dan Iter, Yichong Xu, Shuohang Wang, Ruochen Xu, and Chenguang Zhu. Geval: NLG evaluation using GPT-4 with better human alignment. In Conference on Empirical Methods in Natural Language Processing , 2023.

- [31] Alessio Mazzetto, Dylan Sam, Andrew Park, Eli Upfal, and Stephen Bach. Semi-supervised aggregation of dependent weak supervision sources with performance guarantees. In Conference on Artificial Intelligence and Statistics , 2021.

- [32] Blazej Miasojedow and Wojciech Rejchel. Sparse estimation in Ising model via penalized Monte Carlo methods. Journal of Machine Learning Research , 19(75):1-26, 2018.

- [33] OpenAI. gpt-oss-120b & gpt-oss-20b model card. arXiv:2508.10925 , 2025.

- [34] Draˇ zen Prelec, H Sebastian Seung, and John McCoy. A solution to the single-question crowd wisdom problem. Nature , 541(7638):532-535, 2017.

- [35] Vikas C. Raykar, Shipeng Yu, Linda H. Zhao, Gerardo Hermosillo Valadez, Charles Florin, Luca Bogoni, and Linda Moy. Learning from crowds. Journal of Machine Learning Research , 11:1297-1322, 2010.

- [36] Utkir A Rozikov. Gibbs measures in biology and physics: The Potts model . World Scientific, 2022.

- [37] Abigail See, Peter J. Liu, and Christopher D. Manning. Get to the point: Summarization with pointer-generator networks. In Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers) , 2017.

- [38] Uri Shaham, Xiuyuan Cheng, Omer Dror, Ariel Jaffe, Boaz Nadler, Joseph Chang, and Yuval Kluger. A deep learning approach to unsupervised ensemble learning. In International Conference on Machine Learning , 2016.

- [39] Jacob Steinhardt, Gregory Valiant, and Moses Charikar. Avoiding imposters and delinquents: Adversarial crowdsourcing and peer prediction. Advances in Neural Information Processing Systems , 29, 2016.

- [40] Peter Welinder, Steve Branson, Serge J. Belongie, and Pietro Perona. The multidimensional wisdom of crowds. In Conference on Neural Information Processing Systems , 2010.

- [41] Emily Wenger and Yoed Kenett. We're different, we're the same: Creative homogeneity across LLMs. arXiv:2501.19361 , 2025.

- [42] Jacob Whitehill, Paul Ruvolo, Tingfan Wu, Jacob Bergsma, and Javier R. Movellan. Whose vote should count more: Optimal integration of labels from labelers of unknown expertise. In Conference on Neural Information Processing Systems , 2009.

- [43] Qi Xu, Yubai Yuan, Junhui Wang, and Annie Qu. Crowdsourcing utilizing subgroup structure of latent factor modeling. Journal of the American Statistical Association , 119(546):1192-1204, 2024.

- [44] Yi Yang, Wen-tau Yih, and Christopher Meek. WikiQA: A challenge dataset for open-domain question answering. In Conference on Empirical Methods in Natural Language Processing , 2015.

- [45] Lianmin Zheng, Wei-Lin Chiang, Ying Sheng, Siyuan Zhuang, Zhanghao Wu, Yonghao Zhuang, Zi Lin, Zhuohan Li, Dacheng Li, Eric Xing, Hao Zhang, Joseph E. Gonzalez, and Ion Stoica. Judging LLM-as-a-judge with MT-bench and chatbot arena. In Conference on Neural Information Processing Systems (Datasets and Benchmarks Track) , 2023.

## A Related Works

The LLM-as-a-judge literature uses LLMs to approximate human preferences in open-ended evaluation, including MT-Bench/Chatbot Arena [45] and prompt-based evaluators such as G-Eval [30], as well as benchmark suites like AlpacaEval and debiasing methods for judge preferences (e.g., length control) [15, 28]. See, for example, Gu et al. [19] for a survey and Chen et al. [10], Lee et al. [27] for some recent works.

In the context of binary classification, however, label aggregation has been carried out using majority voting and its weighted variants much before their use in LLM-as-a-judge applications. Our focus is on the case of unsupervised label aggregation in which the unknown true label is treated as a latent variable and EM algorithm is used to infer it. The approach was proposed by Dawid and Skene [12] and analyzed by Berend and Kontorovich [6], Donmez et al. [14], Gao et al. [17], Raykar et al. [35]. A large literature on crowdsourcing extends this template by enriching the annotator/item structure while typically retaining conditional independence of votes given latent variables, e.g., modeling annotator expertise and item difficulty (GLAD) [11, 42, 43], multidimensional annotator effects [40], and incorporating item features jointly with label aggregation (also called as 'learning from crowds') [35]. Bayesian variants and alternatives include Bayesian classifier combination [25] and models designed to detect spammers/adversaries such as MACE [22].

Motivated by economics and customer study literatures [9, 34], recently Ai et al. [2] study LLM aggregation beyond majority vote by proposing optimal weight using first-order statistics and Inverse Surprising Popularity using second-order cross-agent conditional response statistics with theoretical improvements and empirical gains. But their main guarantees effectively assume oraclequality second-order information P ( J i | J j ) for Judges i and j (treated as 'accurate' before finitesample estimation), which can be sample-hungry to estimate and can be brittle under distribution shift or latent-difficulty confounding that changes apparent correlations. Furthermore, they assume the judge labels are conditionally independent given the true label.

While the aforementioned works document biases and variance in LLM judging, they typically aggregate multiple judge calls using independence-based heuristics; our focus is on explicitly modeling and exploiting dependence among judges (e.g., shared prompts or shared failure modes) via Ising structure.

Initial steps towards handling dependencies have been taken by Jaffe et al. [23] and Shaham et al. [38]. In particular, these works study the case of hierarchically dependent judges/annotators, a relaxation of fully conditionally independent judges. While appropriate for certain crowdsourcing applications (e.g., workers clustered by source or organization), this assumption is poorly aligned with LLM-as-a-judge settings: dependencies among LLM judges are rarely tree-structured or nested, and instead arise from overlapping pretraining data, shared architectures, and reused prompting templates that induce dense, non-hierarchical correlations and shared failure modes. As a result, hierarchical-dependence models can miss the dominant correlation patterns in practice and provide limited guidance for correcting over-counted agreement in modern LLM evaluation pipelines. Mazzetto et al. [31] studied a setting where not all the judges are conditionally independent, however a subset of them are. Their approach, however, is fundamentally semi-supervised

## Appendix

meaning that they required some amount of labeled data. We also remark that in the fullysupervised setting, several works [26, 39] considered adversarial annotators which maybe arbitrarily correlated. Compared to these works, our focus is in the purely unsupervised setting.

Finally, we remark that recent works have used additional human (supervised) annotated labels to improve the unknown label inference via the framework of prediction powered inference; see, for example [3, 4, 8]. While we work under the purely unsupervised setting, we remark that our proposed models integrate seamlessly with the aforementioned framework.

## B Motivating Example

Consider three LLM annotators producing binary votes. Annotators 1 and 3 share substantial training data and prompt templates, so their outputs are highly correlated (they tend to agree, including on shared mistakes). Annotator 2 uses a different prompt style and often behaves differently from the other two. These agreement/disagreement patterns are driven by shared modeling choices and therefore persist regardless of the true class label . Consequently, certain vote patterns primarily reflect shared failure modes rather than independent evidence.

Under CI, methods such as the Dawid-Skene method, treats annotator votes as independent given Y , and therefore interprets agreement as multiple independent pieces of evidence. In contrast, an Ising model explicitly represents dependencies via pairwise interactions, allowing the posterior to correctly discount redundant agreement and to recognize 'unlikely' vote configurations created by structural correlations.

We now give a concrete population example in which the a CI-predictor predicts the opposite label from the Bayes-optimal predictor under a class-independent Ising model, even though CI is given the correct one-dimensional marginals .

We now consider a single item ( n = 1) with label Y ∈ { 0 , 1 } and three annotators

<!-- formula-not-decoded -->

with a uniform prior P( Y = 1) = P( Y = 0) = 1 2 . We interpret J k = 1 as annotator k voting for class 1 and J k = 0 as voting for class 0.

We now consider the case when the judge labels are generated from the class-independent coupling Ising model

̸

<!-- formula-not-decoded -->

where the coupling matrix W is shared across classes (capturing label-independent dependence), and only the fields h ( y ) depend on y . In this numerical instance,

<!-- formula-not-decoded -->

Here W 13 > 0 encourages annotators 1 and 3 to co-activate, while W 12 , W 23 < 0 discourage annotator 2 from co-activating with annotators 1 and 3; this encodes the ' { 1 , 3 } similar, 2 different' structure.

Since there are only 2 3 = 8 vote patterns, we can normalize (9) exactly by enumeration. The resulting conditional distributions are:

| ( J 1 ,J 2 ,J 3 ) | P( J | Y = 0) | P( J | Y = 1) |
|---------------------|----------------------|----------------------|
| (0 , 0 , 0) | 0 . 00181 | 0 . 3196 |
| (0 , 0 , 1) | 0 . 0603 | 0 . 0202 |
| (0 , 1 , 0) | 0 . 0180 | 0 . 3796 |
| (0 , 1 , 1) | 0 . 00483 | 1 . 93 × 10 - 4 |
| (1 , 0 , 0) | 3 . 16 × 10 - 4 | 0 . 0428 |
| (1 , 0 , 1) | 0 . 9099 | 0 . 2342 |
| (1 , 1 , 0) | 2 . 01 × 10 - 4 | 0 . 00325 |
| (1 , 1 , 1) | 0 . 00465 | 1 . 43 × 10 - 4 |

We first calculate the Bayes-optimal posterior under the true Ising model. Consider the observed votes

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

With a uniform prior,

<!-- formula-not-decoded -->

Thus the Bayes-optimal prediction is Y = 0.

Next we show that a CI-predictor, i.e., assuming conditional independence across judges predicts the opposite label. Let

<!-- formula-not-decoded -->

denote the true class-conditional one-dimensional marginals implied by the Ising model (9). From the table (summing over the other coordinates),

<!-- formula-not-decoded -->

The CI likelihood replaces the true joint distribution by the product of these marginals:

<!-- formula-not-decoded -->

From the table,

For J = (0 , 1 , 1),

<!-- formula-not-decoded -->

Therefore, with the same uniform prior,

<!-- formula-not-decoded -->

so the CI-predictor generates Y = 1 with high confidence.

This example isolates a purely model-misspecification effect: CI is fed the correct class-conditional marginals ( π ( y ) k ), but it still fails because it assumes independence. The true Ising model assigns

extremely low probability to J = (0 , 1 , 1) under Y = 1 (about 1 . 9 × 10 -4 ), reflecting the fact that the vote pattern is structurally inconsistent with the label-independent correlation pattern encoded by W . CI cannot represent this structural constraint and therefore overestimates P( J | Y = 1) by orders of magnitude, leading to the wrong posterior label.

̸

If dependence patterns also differ by class (i.e., W (1) = W (0) ), then the Bayes log-odds contains quadratic terms J i J j and the same phenomenon can be even more pronounced. For example, with

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

and P( Y = 1) = 1 2 , the observation J = (1 , 1 , 0) satisfies

<!-- formula-not-decoded -->

so Bayes predicts Y = 0 (posterior ≈ 0 . 031), whereas CI built from the correct marginals yields P CI ( Y = 1 | J ) ≈ 0 . 957 and predicts Y = 1. This illustrates the same qualitative failure mode when class information appears directly in correlation differences.

## C Additional Discussion on the Models

## C.1 Conditionally Independent Model with Asymmetric Errors

For the sake of completeness, we introduce the conditionally independent model which assume asymmetric errors. We assume that, conditional on Y i , judges act independently and their accuracies do not depend on the item index i . For each judge j ∈ { 1 , . . . , K } define the sensitivity and specificity

<!-- formula-not-decoded -->

Equivalently, the false-negative and false-positive rates are

<!-- formula-not-decoded -->

Let π := P( Y i = 1) denote the class prior. The generative model is

<!-- formula-not-decoded -->

independently across judges j and items i given the parameters. When parameters are unknown, a convenient conjugate choice is independent Beta priors

<!-- formula-not-decoded -->

with density proportional to p a -1 (1 -p ) b -1 on [0 , 1]. The next result gives the exact posterior log-odds under CI when ( α, β, π ) are known (or when a plug-in estimate is used). The posterior log-odds satisfies

<!-- formula-not-decoded -->

Equivalently, (11) can be written as an affine (weighted-vote) score:

<!-- formula-not-decoded -->

Hence the Bayes-optimal CI decision rule is the weighted majority vote , given by

<!-- formula-not-decoded -->

The weight w j is positive iff α j + β j > 1, i.e., judge j is better than random guessing; it is negative for adversarial judges. In the symmetric special case α j = β j = p j , one obtains w j = 2log p j 1 -p j and an intercept depending on π , recovering the familiar weighted-majority log-odds form under conditional independence.

## C.2 Relation to LDA and QDA

The separation between conditional-independence aggregation and class-dependent Ising aggregation is closely analogous to the classical gap between linear and quadratic discriminant analysis in Gaussian classification. In the Gaussian setting, the Bayes log-likelihood ratio for x ∈ R d takes the form

<!-- formula-not-decoded -->

where c is constant and the quadratic term x ⊤ Ax vanishes exactly when the class covariances coincide (Σ 0 = Σ 1 ), yielding LDA; otherwise QDA is optimal and the decision boundary is quadratic. In our discrete vote setting with J ∈ { 0 , 1 } K , the class-dependent Ising model yields an exactly analogous decomposition:

<!-- formula-not-decoded -->

̸

so the Bayes decision boundary is quadratic in the votes whenever W (1) = W (0) , and it collapses to a linear weighted vote precisely when couplings are shared across classes ( W (1) = W (0) ). From this perspective, the Ising coupling matrix W plays a role analogous to second-order structure (covariance/precision) in Gaussian models, and ∆ Z = -log Z (1) +log Z (0) is the discrete analog of the log-determinant term that appears in QDA.

The analogy is not merely formal: both frameworks say that when class information lives in dependence structure rather than only in marginals , linear/CI rules can be fundamentally misspecified. In particular, just as QDA can separate classes even when means coincide but covariances differ, a class-dependent Ising model can separate classes even when one-dimensional marginals are uninformative, provided the pairwise interaction patterns differ across classes. This is exactly the mechanism behind our separation results (proved later in Section 3): CI uses only products of marginals (a linear log-odds in J ), so it cannot exploit label-dependent correlations encoded by ∆ W and can remain strictly suboptimal. At the same time, there are important differences from the Gaussian discriminant analysis problem. In particular, the statistical/computational trade-off is sharper for Ising models because likelihood evaluation involves partition functions, motivating pseudo-likelihood/approximate inference in EM. We leave a detailed examination of this tradeoff for future work.

## C.3 Relation to Factor Model

While our focus so far has been on Ising models for capturing dependency, yet another class of models widely used to capture dependencies are factor models. In the context of unsupervised aggregation, Whitehill et al. [42] and Xu et al. [43] study factor models to handle potential latent dependencies between the annotators. It is hence natural to explore the connections between the two classes of models. Below, we show that such latent-factor models are approximate special cases of the class-independent Ising models. To the best of our knowledge, this connection has not been observed in the literature despite a considerable amount of work on both models.

Proposition 1 (Latent-factor ⇒ low-rank class-independent Ising couplings to second order) . Fix K,r ∈ N and let J = ( J 1 , . . . , J K ) ∈ { 0 , 1 } K . Let σ ( t ) = (1 + e -t ) -1 and define η j ( y ) := a j y + b j for y ∈ { 0 , 1 } . Let Z ∼ N (0 , I r ) be independent of Y ∼ Bernoulli( π ) , and assume that conditional on ( Y = y, Z = z ) ,

<!-- formula-not-decoded -->

independently over j . Let ε > 0 and define the loadings as λ j = ε ˜ λ j with fixed ˜ λ j ∈ R r satisfying max j ∥ ˜ λ j ∥ ≤ L . Let ˜ Λ ∈ R K × r have rows ˜ λ ⊤ j so that Λ = ε ˜ Λ . For a fixed class y ∈ { 0 , 1 } write η j = η j ( y ) and p j := σ ( η j ) .

Then there exist C y ( ε ) independent of J and a remainder R y ( J ; ε ) such that, for all ε small enough,

̸

<!-- formula-not-decoded -->

where the (class-dependent) fields admit the explicit second-order expansion

̸

<!-- formula-not-decoded -->

and the remainder is uniformly bounded as

<!-- formula-not-decoded -->

for constants C, C ′ > 0 depending only on r and { η j ( y ) } j ≤ K (in particular, not on J or ε ).

In particular, the second-order truncation is a quadratic binary MRF with pairwise couplings given by the off-diagonal entries of the rank-≤ r matrix ΛΛ ⊤ , since (ΛΛ ⊤ ) jk = λ ⊤ j λ k ). The diagonal entries of ΛΛ ⊤ correspond to J 2 j = J j terms and may be absorbed into the fields.

Proof. Fix y ∈ { 0 , 1 } and abbreviate η j = η j ( y ) and p j = σ ( η j ). Write g ( t ) := log(1 + e t ) so that g ′ ( t ) = σ ( t ), g ′′ ( t ) = σ ( t )(1 -σ ( t )), and

<!-- formula-not-decoded -->

We first start with the following integral representation. Conditional on Z = z , we have that

<!-- formula-not-decoded -->

Hence, marginalizing over Z , we obtain

<!-- formula-not-decoded -->

where ϕ r is the standard r -variate Gaussian density and

<!-- formula-not-decoded -->

We now do a second-order Taylor expansion in λ ⊤ j z . By Taylor's theorem, for each ℓ ∈ R ,

<!-- formula-not-decoded -->

for some θ = θ ( ℓ ) ∈ (0 , 1). Therefore

<!-- formula-not-decoded -->

Applying (16) with ℓ = λ ⊤ j z yields the exact decomposition

<!-- formula-not-decoded -->

where

<!-- formula-not-decoded -->

and the remainder is

By (17), we have that

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

Combining with ϕ r ( z ) ∝ e -∥ z ∥ 2 / 2 gives the following integral representation:

<!-- formula-not-decoded -->

We now derive an exact Gaussian integral for the quadratic part. For ε small enough, ∥ M ∥ < 1 (indeed ∥ M ∥ ≤ 1 4 ∑ j ∥ λ j ∥ 2 ) so I + M ≻ 0. Let Σ := ( I + M ) -1 and µ := Σ u . Then

<!-- formula-not-decoded -->

and hence

<!-- formula-not-decoded -->

where uniformly over J .

Next, we expand the quadratic Gaussian terms. Since ∥ M ∥ = O ( ε 2 B 2 ), we have

<!-- formula-not-decoded -->

Therefore

<!-- formula-not-decoded -->

We now proceed with bounding ∆( J ; ε ) from (19). Define B 2 := ∑ K j =1 ∥ ˜ λ j ∥ 2 and B 3 := ∑ K j =1 ∥ ˜ λ j ∥ 3 . Since λ j = ε ˜ λ j , (18) implies

<!-- formula-not-decoded -->

Also, u = O ( ε ) uniformly in J because | J j -p j | ≤ 1 gives

<!-- formula-not-decoded -->

Moreover, ∥ M ∥ = O ( ε 2 ) uniformly in J (in fact M does not depend on J ), so for ε small the eigenvalues of Σ = ( I + M ) -1 are bounded above and below by absolute constants, and ∥ µ ∥ = ∥ Σ u ∥ = O ( ε ) uniformly in J .

Let Z ∼ N ( µ, Σ) and set R := ε -1 / 2 . Split

<!-- formula-not-decoded -->

On {∥ Z ∥ ≤ R } we have |R ( Z ) | ≤ 1 24 ε 3 B 3 R 3 = 1 24 ε 3 / 2 B 3 , which is ≤ 1 / 2 for ε small (since B 3 is fixed). Therefore | e R ( Z ) -1 | ≤ 2 |R ( Z ) | on {∥ Z ∥ ≤ R } and

<!-- formula-not-decoded -->

using E ∥ Z ∥ 3 < ∞ (uniformly in J ) and the bound on |R| .

For the tail term, one can use a quadratic-envelope bound ensuring e R ( Z ) is at most Gaussianquadratic in Z (because g ′′ ( · ) ≤ 1 / 4), yielding e R ( Z ) ≤ exp( c ε 2 B 2 ∥ Z ∥ 2 ) for a constant c depending only on { η j } . Since Z is Gaussian with covariance uniformly comparable to I r ,

<!-- formula-not-decoded -->

for some c ′ > 0 and all ε small enough (uniformly in J ).

Combining these bounds shows that

<!-- formula-not-decoded -->

and hence, for ε small enough so that | E [ e R ( Z ) ] -1 | ≤ 1 / 2,

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

where C ( J ) is constant in J and the J -independent pieces are absorbed into C y ( ε ). Plugging into (19) yields

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

It remains now to extract the fields and the couplings from u ⊤ u . Recall u = ∑ K j =1 ( J j -p j ) λ j . Then

<!-- formula-not-decoded -->

̸

Expanding ( J j -p j )( J k -p k ) and separating the j = k and j = k parts gives

̸

<!-- formula-not-decoded -->

̸

Absorbing the constant into C y ( ε ) yields (13)-(14). Finally, the bound (15) follows from B 3 ≤ (max j ∥ ˜ λ j ∥ ) B 2 .

Remark 2 (Ising on ± 1 spins and the choice of label set for Y ) . The result is naturally stated with Y ∈ { 0 , 1 } here since Y ∼ Bernoulli( π ) and η j ( y ) = a j y + b j . If one prefers Y ∈ {± 1 } , set ˜ Y := 2 Y -1 and rewrite η j ( Y ) = b j + a j Y = ( b j + 1 2 a j ) + ( 1 2 a j ) ˜ Y .

For the observed binary variables, define spins X j := 2 J j -1 ∈ {± 1 } . Then J j = ( X j +1) / 2 , and any quadratic MRF

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

̸

with ˜ W jk = b jk / 4 and ˜ h j = a j / 2 + 1 4 ∑ k = j b jk . Thus, in (13) , the {± 1 } couplings are ˜ W jk = ( λ ⊤ j λ k ) / 4 up to O ( ε 3 ) , and the low-rank structure is preserved (scaling does not change rank).

Remark 3. The reduction from a latent-factor model to an (approximately) pairwise Ising model is inherently a local approximation in a 'coupling strength' parameter. When ε is not small, the neglected terms in L ( y ) ε ( J ) need not be well-approximated by a pairwise Ising energy. The next terms in the Taylor/cumulant expansion generate higher-order interactions : in general,

<!-- formula-not-decoded -->

where the leading triple-interaction coefficients scale like

<!-- formula-not-decoded -->

with becomes an Ising model

̸

(and more generally the orderm coefficients scale with ε m times the m th cumulant of Z and higher derivatives of A ). Therefore, if the latent factor distribution is non-Gaussian (skewed, so κ 3 ( Z ) = 0 ), a third-order Ising/log-linear model (i.e., adding J j J k J ℓ terms) is the natural next approximation beyond pairwise. In the logistic-normal case we considered (i.e., Z Gaussian with mean zero), κ 3 ( Z ) = 0 so the leading correction after the pairwise term typically begins at order ε 4 (corresponding to four-way interactions); nevertheless, for moderate-to-large ε it can still be important to move beyond pairwise models, either by fitting a higher-order log-linear model as in (20) or by performing inference directly in the latent-factor model without truncating the expansion.

## C.3.1 Suboptimality of CI-Posterior under Latent-factors

We now show a separation result between (exchangeable) latent-factor models and conditionally independent models. Fix parameters a, b, λ ∈ R and σ 2 Z > 0, and let σ ( t ) = (1 + e -t ) -1 denote the logistic function. Let Z ∼ N (0 , σ 2 Z ) be a scalar latent factor independent of Y . Conditional on ( Y = y, Z = z ), the K judges produce i.i.d. votes

<!-- formula-not-decoded -->

̸

We now discuss the true posterior and Bayes rule under these model. Let P ⋆ ( · | J ) denote the posterior under the true model (21), and define the Bayes predictor

Note that λ = 0 and σ 2 Z > 0 imply a nondegenerate factor that induces dependence among judges given Y . Write S K = ∑ K j =1 J j and s K = S K /K .

<!-- formula-not-decoded -->

Conditional-independence (CI) Predictor. Define the class-conditional marginal success probabilities

<!-- formula-not-decoded -->

The CI approximation replaces the true joint likelihood by the product of marginal Bernoulli likelihoods, i.e.,

<!-- formula-not-decoded -->

Let P ind ( · | J ) be the posterior induced by L ind y and prior π , and define

<!-- formula-not-decoded -->

Define the Bernoulli KL divergence for s, q ∈ (0 , 1) by

<!-- formula-not-decoded -->

̸

Theorem 3 (Asymptotic Bayes-CI separation under an exchangeable logistic-normal factor) . Assume the exchangeable latent-factor model (21) with λ = 0 and σ 2 Z > 0 . Let S K = ∑ K j =1 J j and s K = S K /K . Write q y := P marg ( y ) = E Z [P( y, Z )] ∈ (0 , 1) . Define, for s ∈ (0 , 1) ,

<!-- formula-not-decoded -->

and

<!-- formula-not-decoded -->

Let s ∞ := p ( Y, Z ) ∈ (0 , 1) .

Assume the (mild) no-tie conditions

<!-- formula-not-decoded -->

Then, as K →∞ ,

<!-- formula-not-decoded -->

and the excess risk has the limit

<!-- formula-not-decoded -->

̸

̸

In particular, if P( g ind ∞ = g ⋆ ∞ ) > 0 , then the limit is strictly positive.

Proof. We start with a reduction to the sufficient statistic S K . Fix y ∈ { 0 , 1 } and let j = ( j 1 , . . . , j K ) ∈ { 0 , 1 } K with ∑ K k =1 j k = S . Under (21), we have that

<!-- formula-not-decoded -->

which depends on j only through S . Hence S K is sufficient for Y under the true model, and likewise S K is sufficient under the CI model by construction. Therefore both posteriors and both decision rules can be written as functions of S K (equivalently s K ).

We next derive almost sure limits of the vote fraction. First condition on ( Y = y, Z = z ). Then J 1 , . . . , J K are i.i.d. Bernoulli( p ( y, z )), so by the strong law, s K → p ( y, z ) almost surely. Unconditioning yields s K → p ( Y, Z ) =: s ∞ almost surely.

We now derive sharp asymptotics of the true marginal likelihood L ⋆ y ( S ). Recall

<!-- formula-not-decoded -->

Fix s ∈ (0 , 1) and take S = ⌊ Ks ⌋ (so S/K → s ). By Stirling's formula, uniformly for s in any compact [ ε, 1 -ε ] ⊂ (0 , 1),

<!-- formula-not-decoded -->

Furthermore, we have that

<!-- formula-not-decoded -->

Now, using the identity

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

gives

uniformly for s in compact subsets of (0 , 1).

̸

Because λ = 0, the map z ↦→ p ( y, z ) is strictly monotone and continuous with range (0 , 1). Hence for each s ∈ (0 , 1) there is a unique z y ( s ) ∈ R such that p ( y, z y ( s )) = s . Since KL ( s ∥ q ) ≥ 0 with equality iff q = s , we have ψ y ( z ; s ) ≥ 0 with a unique minimizer at z = z y ( s ) and ψ y ( z y ( s ); s ) = 0.

Moreover, ψ y ( · ; s ) has a nondegenerate quadratic minimum at z y ( s ). Indeed, write q ( z ) := p ( y, z ) and note that for fixed s ,

<!-- formula-not-decoded -->

By the chain rule and q ′ ( z ) = λ (2 y -1) q ( z )(1 -q ( z )), we get at z = z y ( s ) (where q ( z ) = s )

<!-- formula-not-decoded -->

Therefore Laplace's approximation method (for an interior, nondegenerate minimum) yields, uniformly for s in compact subsets of (0 , 1),

<!-- formula-not-decoded -->

Combining the last two displays gives the desired sharp 1 /K -scale asymptotic:

<!-- formula-not-decoded -->

In the above f y is indeed exactly the density of the transformed random variable p ( y, Z ) by change of variables.

We now proceed with the limit of the true posterior and Bayes decision. By the aforementioned sufficiency argument, we have that

<!-- formula-not-decoded -->

Let s K = S K /K → s ∞ almost surely by Step 1. Applying (22) to the (random) sequence s K (using local uniformity on a neighborhood of the a.s. limit point s ∞ ∈ (0 , 1)), we obtain almost surely

<!-- formula-not-decoded -->

Now compute f 1 /f 0 explicitly. Writing θ := logit( s ), the unique solutions to p ( y, z ) = s are

<!-- formula-not-decoded -->

The Jacobian factors in (22) cancel because | λ | is the same for y = 0 , 1, so

<!-- formula-not-decoded -->

A direct algebraic simplification gives

<!-- formula-not-decoded -->

Hence

<!-- formula-not-decoded -->

and therefore almost surely

̸

<!-- formula-not-decoded -->

Since g ⋆ K = 1 { η K ≥ 1 / 2 } and P( ℓ ⋆ ( s ∞ ) = 0) = 0 by assumption, the sign stabilizes and

<!-- formula-not-decoded -->

Next, we derive the limit of the CI decision rule. Under CI, we have that

<!-- formula-not-decoded -->

Thus the CI log-posterior odds equal

<!-- formula-not-decoded -->

Since s K → s ∞ almost surely and P( ℓ ind ( s ∞ ) = 0) = 0, the term Kℓ ind ( s K ) diverges to ±∞ with the sign of ℓ ind ( s ∞ ), hence

<!-- formula-not-decoded -->

We are now ready to calculate the excess risks. For any (measurable) classifier g ( J ) ∈ { 0 , 1 } ,

̸

<!-- formula-not-decoded -->

The Bayes rule g ⋆ K = 1 { η K ≥ 1 / 2 } minimizes this conditional risk, and a direct case check gives

̸

<!-- formula-not-decoded -->

̸

̸

Taking expectations and substituting g = g ind K yields the exact finiteK identity

̸

<!-- formula-not-decoded -->

Note that we also have η K → η ∞ and g ind K → g ind ∞ and g ⋆ K → g ⋆ ∞ almost surely. Since the integrand is bounded by 1, dominated convergence gives

̸

<!-- formula-not-decoded -->

̸

̸

Finally, on the event { g ind ∞ = g ⋆ ∞ } we must have η ∞ = 1 / 2 (since g ⋆ ∞ is the threshold at 1 / 2), so | 2 η ∞ -1 | > 0 there; thus if P( g ind ∞ = g ⋆ ∞ ) > 0 the expectation is strictly positive.

Theorem 3 formalizes a simple but important phenomenon: if the judges share a common latent factor that affects their votes, then their votes are dependent given the label, and a CI-predictor can remain strictly suboptimal even as the number of judges K grows.

In the logistic-normal factor model, conditional on the label Y and a latent scalar Z , the judges vote independently:

<!-- formula-not-decoded -->

The key point is that Z is shared across all judges for a given item, so after marginalizing out Z the votes are no longer independent given Y . Equivalently, Z induces a label-dependent correlation/failure mode (e.g. shared bias, shared noise, or common difficulty of the item).

Now, we discuss the case what happens when K → ∞ . As the number of judges grows, the empirical vote fraction

<!-- formula-not-decoded -->

concentrates almost surely around the random limit

<!-- formula-not-decoded -->

Thus, with many judges, the data effectively reveals the latent factor through the realized value of s ∞ (because different Z values shift the success probability).

The Bayes posterior P( Y = 1 | J ) integrates over Z using the correct mixture likelihood. In this specific logistic-normal setup, the largeK limit of the Bayes posterior depends on s ∞ through an explicit one-dimensional score

<!-- formula-not-decoded -->

so the Bayes predictor converges to the limiting rule

<!-- formula-not-decoded -->

Intuitively, Bayes predictor recognizes that extreme values of the vote fraction s ∞ may be better explained by certain Z realizations under one class than the other.

Under CI the true joint likelihood is replaced by a product of class-conditional marginals. This yields a different limiting score,

<!-- formula-not-decoded -->

and hence a potentially different limiting decision

<!-- formula-not-decoded -->

Because CI discards the correlation structure induced by Z , it generally assigns different relative likelihoods to the same observed vote fraction s ∞ than the true Bayes model does.

In summary, the proposition shows that both rules converge (almost surely) to deterministic limit classifiers that depend only on s ∞ = p ( Y, Z ). Moreover, it gives an exact expression for the asymptotic excess risk:

̸

<!-- formula-not-decoded -->

where η ∞ is the limiting Bayes posterior. This quantity is strictly positive whenever the limiting CI and Bayes decisions disagree on a set of latent-factor realizations of positive probability. In other words, adding more judges does not necessarily save CI; as K grows, the ensemble increasingly reveals the shared latent factor, and Bayes exploits it, but CI cannot, so the performance gap can converge to a nonzero constant.

## D Posterior Inference with Unknown Labels via (Generalized) EM

Recall that, all models in this paper share the same high-level structure: each item i ∈ { 1 , . . . , n } has an unobserved label Y i ∈ { 0 , 1 } and an observed vote vector J i = ( J i 1 , . . . , J iK ) ∈ { 0 , 1 } K . The joint model factorizes across items as

<!-- formula-not-decoded -->

where Θ denotes model parameters (e.g., CI accuracies, Ising fields/couplings, latent-factor loadings, etc.). The inferential goal is to compute the posterior label probabilities γ i := P Θ ( Y i = 1 | J i ) , i = 1 , . . . , n, and to produce point predictions ˆ Y i = 1 { γ i ≥ 1 / 2 } .

We use the Expectation-Maximization framework [12] for the above purpose. The observed-data log-likelihood is

<!-- formula-not-decoded -->

EM maximizes ℓ (Θ) by iteratively optimizing a lower bound based on the complete-data loglikelihood. Given current parameters Θ ( t ) , define

<!-- formula-not-decoded -->

The expected complete-data objective (the Q -function) is then given by

<!-- formula-not-decoded -->

When we include regularization or Bayesian priors, we maximize Q (Θ | Θ ( t ) ) + log P(Θ) instead (MAP-EM). The overall procedure is provided in Algorithm 1. We emphasize that the procedure is purely unsupervised.

## D.1 Specializations of Algorithm 1

In the conditionally independent (CI) family, including Dawid-Skene and its asymmetric sensitivity/specificity variants, the class-conditional likelihood factorizes across judges: P Θ ( J i | Y i = y ) = ∏ K j =1 P Θ ( J ij | Y i = y ) . As a result, the E-step is exact and inexpensive: the score difference ̂ ℓ i 1 -̂ ℓ i 0 is just a sum of per-judge log-likelihood ratios, yielding closed-form responsibilities γ i via a logistic transform. The M-step is also simple: maximizing (26) reduces to fitting per-judge Bernoulli parameters from soft counts, i.e., weighted averages of votes under γ i (and 1 -γ i ), together with the closed-form update for the class prior. This recovers the classical David-Skene EM algorithm [12] as a special case of Algorithm 1.

For latent-factor models, the conditional likelihood typically has the form P Θ ( J i | Y i = y ) = ∫ P Θ ( J i | Y i = y, Z i = z ) P Θ ( z ) dz, where Z i is a per-item latent variable (e.g., item difficulty, topic,

## Algorithm 1 Generalized EM for unsupervised binary label aggregation (CI, latent factors, Ising)

- 1: Input: votes J i ∈ { 0 , 1 } K for i = 1 , . . . , n ; model family P Θ ( J | Y ); initialization Θ (0) ; tolerances.
- 2: for t = 0 , 1 , 2 , . . . until convergence do
- 3: E-step (posterior labels): For each item i , compute class scores

<!-- formula-not-decoded -->

using an exact evaluator (when tractable) or an approximation (e.g. mean-field, loopy BP, Monte Carlo, or a variational bound). Set

<!-- formula-not-decoded -->

where σ ( u ) = (1 + e -u ) -1 .

- 4: M-step (parameter update): Update the class prior (MLE form)

<!-- formula-not-decoded -->

Update remaining parameters by (approximately) maximizing the weighted objective

<!-- formula-not-decoded -->

using a model-appropriate solver (closed-form updates, gradient methods, pseudo-likelihood, etc.).

- 5: end for
- 6: Output: parameters ̂ Θ and posteriors ̂ γ i ; predicted labels ̂ Y i = 1 { ̂ γ i ≥ 1 / 2 } .

or shared failure mode). The E-step therefore requires marginalizing over Z i , which is generally not available in closed form in flexible models. In practice one can compute approximate class scores ̂ ℓ iy using a tractable approximation to the integral, such as a variational bound, Laplace approximation, or Monte Carlo estimate, and then form γ i as in (25). The M-step becomes a (regularized) maximum-likelihood or MAP problem for the latent-factor parameters (loadings, biases, prior variance, etc.) with soft labels; we solve it with gradient-based optimization, optionally interleaving updates for per-item latent posterior parameters (as in variational EM) when a fully Bayesian treatment of Z i is used.

For Ising models, the main difficulty is that the exact likelihood P Θ ( J i | Y i = y ) involves the partition function Z ( y ) (Θ), making both the E-step scores and the M-step objective intractable at scale. We therefore use the generalized EM strategy based on tractable surrogates. A standard choice (which we use in our experiments) is the (regularized) pseudo-likelihood [21], which replaces the log-likelihood by a sum of conditional node log-likelihoods ∑ j log P Θ ( J ij | J i, -j , Y i = y ) and avoids Z ( y ) entirely. In the M-step, maximizing (26) under pseudo-likelihood reduces to a set of weighted logistic regressions (one per node) with weights given by the current responsibilities γ i for class y = 1 and (1 -γ i ) for class y = 0. In the E-step, we can compute ̂ ℓ iy either using the

same pseudo-likelihood score (yielding a fully consistent surrogate EM). Other possibilities include using a approximate inference methods including mean-field methods [7], belief propagation [29], or Markov chain Monte Carlo [32] to approximate the true class-conditional evidence.

Finally, we remark that for our experiments in Sections 4.1 and F, when using specific instantiations of Algorithm 1, we manually tune the hyperparameters (if any) for best performance. More principled ways to set them include general purpose procedures like cross-validation.

## D.2 Illustration of Theorem 2 via Algorithm 1

For the sake of the reader's convenience, we connect the magnetization-threshold rule in Theorem 2 to posterior-threshold prediction as in Algorithm 1. Define for each item i the (spin) magnetization

<!-- formula-not-decoded -->

Because the Curie-Weiss model is exchangeable, the Bayes posterior depends on the votes J i only through M i (equivalently through the vote fraction). In particular, if we form a (possibly approximate/plug-in) posterior based on the statistic | M i | ,

<!-- formula-not-decoded -->

where ̂ p y ( · ) denotes the (estimated) class-conditional pmf/density of | M K | under Y = y , then the usual posterior-threshold prediction is

<!-- formula-not-decoded -->

In the Curie-Weiss regimes used for the separation result in Theorem 2, the log-likelihood ratio m ↦→ log ̂ p 1 ( m ) ̂ p 0 ( m ) is (asymptotically) increasing in m ∈ [0 , 1], so there exists a threshold t ∈ (0 , 1) such that

<!-- formula-not-decoded -->

Thus the magnetization classifier ˜ g K ( J ) = 1 {| M K ( J ) | ≥ t } is exactly a posterior-threshold rule of the form ̂ Y i = 1 { ̂ γ i ≥ 1 / 2 } when ̂ γ i is computed from (or approximated by) evidence in | M K | .

## E Proofs from Section 3

## E.1 Proof of Theorem 1

Theorem 1 (Nonvanishing Bayes vs. CI Separation for Class-conditional Ising Models) . Fix a prior P( Y = 1) = π ∈ (0 , 1) . For each K ≥ 1 , let J = ( J 1 , . . . , J K ) ∈ { 0 , 1 } K denote the K judges' votes for a single item and define the recoded spins X j := 2 J j -1 ∈ {-1 , +1 } and let M K := 1 K ∑ K j =1 X j ∈ { -1 , -1 + 2 K , . . . , 1 } . Assume the following class-conditional Curie-Weiss Ising model: there exist constants 0 < β 0 < 1 < β 1 such that, conditional on Y = y ∈ { 0 , 1 } ,

<!-- formula-not-decoded -->

̸

for x ∈ {-1 , +1 } K . Equivalently (writing x j = 2 j j -1 ), this is a special case of the { 0 , 1 } -Ising form (1) with h ( y ) j = -2 β y ( 1 -1 K ) and W ( y ) jk = 4 β y K ( j = k ) , up to an additive constant absorbed into Z ( y ) .

Let g ⋆ K be the Bayes-optimal predictor under the true model (6) . Let g ind K be the population CI-predictor that replaces the true joint by the product of true one-dimensional marginals, i.e., P ind ( J = j | Y = y ) := ∏ K r =1 q j r y (1 -q y ) 1 -j r with q y := P( J r = 1 | Y = y ) ( independent of r ) , and then thresholds the induced posterior P ind ( Y = 1 | J ) at 1 / 2 . Then the following results hold:

1. (CI Collapses to the Prior) For every K and y ∈ { 0 , 1 } , one has q y = 1 2 . Consequently, P ind ( Y = 1 | J ) = π for all J , so g ind K ( J ) ≡ 1 { π ≥ 1 2 } , and R ( g ind K ) = min { π, 1 -π } , ∀ K .
1. (Bayes Risk Vanishes) Let m ⋆ = m ⋆ ( β 1 ) ∈ (0 , 1) denote the unique positive solution to m = tanh( β 1 m ) . Then for any fixed threshold t ∈ (0 , m 2 ⋆ ) , the quadratic statistic test:

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

satisfies R (˜ g K ) → 0 as K →∞ . Hence R ( g ⋆ K ) → 0 as K →∞ .

3. (Nonvanishing Separation) We have:

<!-- formula-not-decoded -->

Proof. We start with the proof of assertion (1).

Fix y ∈ { 0 , 1 } and K . Under (6), the density depends on x only through ( ∑ j x j ) 2 , and hence is invariant under the global spin-flip x ↦→-x :

<!-- formula-not-decoded -->

Therefore, for each coordinate r ,

<!-- formula-not-decoded -->

so E [ X r | Y = y ] = 0 and hence P( X r = +1 | Y = y ) = P( X r = -1 | Y = y ) = 1 2 . Since J r = ( X r +1) / 2, we get q y = P( J r = 1 | Y = y ) = 1 2 for both y = 0 , 1. With q 0 = q 1 = 1 2 , the CI likelihoods coincide:

<!-- formula-not-decoded -->

so Bayes' rule under the CI model gives P ind ( Y = 1 | J ) = π for all J and g ind K ( J ) ≡ 1 { π ≥ 1 2 } . Its (true) misclassification risk is then

̸

<!-- formula-not-decoded -->

This proves assertion (1).

Before proving assertion (2), we require some intermediate results.

We start by proving a magnetization representation and a uniform combinatorial bound for the Ising model case. Fix β > 0 and consider the Curie-Weiss law

<!-- formula-not-decoded -->

For m ∈ {-1 , -1 + 2 /K,... , 1 } , let N K ( m ) be the number of configurations with magnetization M K = m . Writing r = # { j : x j = +1 } = K (1+ m ) 2 , we have N K ( m ) = ( K r ) and

<!-- formula-not-decoded -->

where Z K ( β ) is the corresponding normalizer (sum of the numerator over all admissible m ). Define the binary entropy (natural logs)

<!-- formula-not-decoded -->

and the mean-field objective

<!-- formula-not-decoded -->

A standard consequence of Stirling's bounds is the uniform approximation

<!-- formula-not-decoded -->

Combining (27)-(28) yields

<!-- formula-not-decoded -->

where the sum runs over the ( K + 1) admissible magnetization values and the O (log K ) term is uniform in m,m ′ .

We next identify the location of the maximizers of Φ β .

<!-- formula-not-decoded -->

1. If β < 1 , then Φ β is strictly concave on ( -1 , 1) and has a unique maximizer at m = 0 .
1. If β > 1 , then there exists a unique m ⋆ ( β ) ∈ (0 , 1) solving m = tanh( βm ) . Moreover, Φ β has exactly two global maximizers at ± m ⋆ ( β ) , and m = 0 is a strict local minimum.

Proof. For m ∈ ( -1 , 1), differentiating gives

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

hence

If β < 1, then for all m ∈ ( -1 , 1),

<!-- formula-not-decoded -->

(since 1 / (1 -m 2 ) ≥ 1), so Φ β is strictly concave and has at most one critical point. Because Φ β is even, Φ ′ β (0) = 0, so m = 0 is the unique maximizer.

If β > 1, then Φ ′′ β (0) = β -1 > 0, so m = 0 is a strict local minimum. Critical points satisfy Φ ′ β ( m ) = 0, i.e. arctanh( m ) = βm , equivalently m = tanh( βm ). Define f ( m ) := tanh( βm ) -m on [0 , 1]. Then f (0) = 0 and f ′ (0) = β -1 > 0, while f (1) = tanh( β ) -1 < 0. By continuity, there exists at least one root in (0 , 1). Moreover, f ′ ( m ) = β (1 -tanh 2 ( βm )) -1 = β (1 -m 2 ) -1 at a root (since then tanh( βm ) = m ), and m ↦→ β (1 -m 2 ) -1 is strictly decreasing on [0 , 1]. This implies f is strictly concave on any interval where it is positive and strictly decreasing once m is large enough; in particular, f can cross zero at most once in (0 , 1), so the positive root is unique; call it m ⋆ ( β ). By symmetry, -m ⋆ ( β ) is also a critical point.

At m = ± m ⋆ ( β ), we have β (1 -m 2 ⋆ ( β )) < 1 (equivalently the slope of tanh( βm ) at the intersection is < 1), so Φ ′′ β ( ± m ⋆ ( β )) = -1 1 -m ⋆ ( β ) 2 + β < 0, hence ± m ⋆ ( β ) are strict local maxima. Since Φ β is continuous on compact [ -1 , 1], it attains global maxima; the only candidates are critical points and endpoints. The endpoints satisfy H ( 1 ± 1 2 ) = 0, hence Φ β ( ± 1) = β 2 , while Φ β ( ± m ⋆ ( β )) > Φ β (0) = log 2 for β > 1 (indeed ± m ⋆ ( β ) are maxima and 0 is a local minimum). Thus the global maxima are exactly ± m ⋆ ( β ).

We next show exponential concentration of M K under β 0 and β 1 . Our approach for proving concentration for Curie-Weiss models is motivated by Friedli and Velenik [16, Chapter 2]. While more sophisticated approaches are available to obtain sharp concentration bounds, we use this simpler approach as a coarse concentration result suffices to prove our separation result of interest.

Lemma 2 (Concentration under β < 1) . Fix β ∈ (0 , 1) and δ ∈ (0 , 1) . Then there exists c = c ( β, δ ) > 0 such that

<!-- formula-not-decoded -->

Proof. By assertion (1) of Lemma 1, Φ β has unique maximizer at 0. By continuity of Φ β and compactness of { m ∈ [ -1 , 1] : | m | ≥ δ } ,

<!-- formula-not-decoded -->

Using (29), for the numerator we bound

<!-- formula-not-decoded -->

and for the denominator,

<!-- formula-not-decoded -->

Taking the ratio gives

<!-- formula-not-decoded -->

which is ≤ exp( -cK ) for all large K for any c < ∆.

Lemma 3 (Concentration under β > 1) . Fix β > 1 and let m ⋆ = m ⋆ ( β ) ∈ (0 , 1) be the unique positive solution to m = tanh( βm ) . For any ε ∈ (0 , m ⋆ ) , there exists c = c ( β, ε ) > 0 such that

<!-- formula-not-decoded -->

Proof. By Lemma 1(2), Φ β has exactly two strict global maximizers at ± m ⋆ . Define the closed set

<!-- formula-not-decoded -->

Since ± m ⋆ / ∈ F ε and Φ β is continuous, compactness implies

<!-- formula-not-decoded -->

The same numerator/denominator bounding argument used in Lemma 2 applied to the event { M K ∈ F ε } yields

<!-- formula-not-decoded -->

for any c < ∆ and all sufficiently large K

<!-- formula-not-decoded -->

We are now ready the prove assertion (2).

Consider the joint model from Theorem 1 with β 0 ∈ (0 , 1) and β 1 > 1. Fix any t ∈ (0 , m ⋆ ( β 1 ) 2 ) and define ˜ g K ( J ) = 1 { M K ( J ) 2 ≥ t } .

Type I error under Y = 0 : Conditional on Y = 0, the spins follow P β 0 , hence by Lemma 2 with δ = √ t , √

<!-- formula-not-decoded -->

Type II error under Y = 1 : Conditional on Y = 1, the spins follow P β 1 . Let m ⋆ = m ⋆ ( β 1 ) and set ε := m ⋆ - √ t 2 > 0. If M 2 K < t , then | M K | < √ t = m ⋆ -2 ε , hence ∣ ∣ | M K | -m ⋆ ∣ ∣ ≥ 2 ε . Therefore, by Lemma 3 (applied with 2 ε ),

<!-- formula-not-decoded -->

Combining the two conditional errors,

<!-- formula-not-decoded -->

Since the Bayes predictor g ⋆ K minimizes misclassification risk under the true joint law,

<!-- formula-not-decoded -->

proving assertion (2).

Finally, we immediately have the separation limit stated in assertion (3). Indeed, assertion (1) gives R ( g ind K ) = min { π, 1 -π } for all K , while assertion (2) gives R ( g ⋆ K ) → 0. Hence

<!-- formula-not-decoded -->

This proves assertion (3) and completes the overall proof.

## E.2 Proof of Theorem 2

Theorem 2 (Curie-Weiss separation with informative marginals) . Let Y ∈ { 0 , 1 } with P( Y = 1) = π ∈ (0 , 1) . For each K ≥ 1 , define spins X = ( X 1 , . . . , X K ) ∈ {-1 , +1 } K and votes J j = ( X j +1) / 2 ∈ { 0 , 1 } . Let the class-conditional laws of X be Curie-Weiss models with (possibly K -dependent) external fields:

<!-- formula-not-decoded -->

for y ∈ { 0 , 1 } . Assume parameters satisfy:

1. (High-temperature Class) β 0 ∈ (0 , 1) and h 0 ,K ≡ h 0 < 0 is a fixed negative constant;
1. (Low-temperature Class with Weak Symmetry Breaking) β 1 > 1 and h 1 ,K = c/K with some fixed c > 0 .

Let M K := 1 K ∑ K j =1 X j ∈ [ -1 , 1] be the magnetization. Let m 0 ∈ ( -1 , 0) be the unique solution of the mean-field equation m 0 = tanh( β 0 m 0 + h 0 ) , and let m ⋆ = m ⋆ ( β 1 ) ∈ (0 , 1) be the unique positive solution of m ⋆ = tanh( β 1 m ⋆ ) . Define

<!-- formula-not-decoded -->

Assume additionally that

<!-- formula-not-decoded -->

Let g ⋆ K denote the Bayes predictor under the true model (7) . Let g ind K denote the population CIpredictor that replaces P( J | Y = y ) by the product of the true marginals ∏ K j =1 q J j y (1 -q y ) 1 -J j .Then, the following hold:

1. (Informative Marginals) Each judge is individually better than random: q 0 < 1 2 < q 1 (equivalently, specificity 1 -q 0 > 1 2 and sensitivity q 1 > 1 2 ).
1. (Bayes Risk Vanishes) For any fixed threshold t satisfying | m 0 | < t < m ⋆ , the aggregator ˜ g K ( J ) := 1 {| M K | ≥ t } has R (˜ g K ) → 0 as K →∞ . Consequently, R ( g ⋆ K ) → 0 .
1. (CI Remains Bounded away from Bayes) As K →∞ , we have R ( g ind K ) → π (1 -p ) , and hence lim K →∞ ( R ( g ind K ) -R ( g ⋆ K ) ) ≥ π (1 -p ) > 0 .

Proof. The proof is similar to that of Theorem 1. We start with the magnetization representation. For β > 0 and field h , the Curie-Weiss probability of M K = m (with m ∈ {-1 , -1 + 2 K , . . . , 1 } ) can be written as

<!-- formula-not-decoded -->

where Z K ( β, h ) normalizes the mass over all admissible m . Let H ( p ) = -p log p -(1 -p ) log(1 -p ) and define

Stirling's formula yields

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

uniformly over admissible m , hence

<!-- formula-not-decoded -->

We now compute the marginals correponding to item (1). By exchangeability, E [ X 1 | Y = y ] = E [ M K | Y = y ]. Under ( β 0 , h 0 ) with β 0 ∈ (0 , 1) and fixed h 0 < 0, the standard mean-field analysis implies that M K → m 0 in probability, where m 0 is the unique solution to m = tanh( β 0 m + h 0 ). Hence E [ M K | Y = 0] → m 0 < 0 and

<!-- formula-not-decoded -->

Under ( β 1 , h 1 ,K ) with β 1 > 1 and h 1 ,K = c/K , we show below (Step 2) that M K converges in distribution to a two-point mixture p δ m ⋆ +(1 -p ) δ -m ⋆ with p = σ (2 cm ⋆ ) ∈ (1 / 2 , 1). Therefore E [ M K | Y = 1] → (2 p -1) m ⋆ > 0 and

<!-- formula-not-decoded -->

This proves item (1).

We now examine the magnetization limits under the two classes. Consider Y = 0. Since β 0 < 1, Φ β 0 is strictly concave on ( -1 , 1) and has a unique maximizer; adding the linear term h 0 m preserves uniqueness. Thus the exponent in (31) has a unique global maximizer at m 0 , and a standard Laplace argument yields

<!-- formula-not-decoded -->

Now consider Y = 1. Here h 1 ,K = c/K , so h 1 ,K K = c and (31) becomes

<!-- formula-not-decoded -->

For β 1 > 1, Φ β 1 has exactly two global maximizers at ± m ⋆ (where m ⋆ = tanh( β 1 m ⋆ )). Fix ε ∈ (0 , m ⋆ ) and define neighborhoods

<!-- formula-not-decoded -->

By continuity and strict maximality at ± m ⋆ , there exists ∆( ε ) > 0 such that sup m ∈ F ε Φ β 1 ( m ) ≤ Φ β 1 ( m ⋆ ) -∆( ε ). Using (33) and the same numerator/denominator bounding argument as in Lemma 3, we obtain exponential concentration:

<!-- formula-not-decoded -->

Hence | M K |→ m ⋆ in probability under Y = 1.

It remains to identify the limiting mixture weights . Let A K, + (resp. A K, -) denote the total unnormalized mass in U + (resp. U -) in (33). On U + we have m = m ⋆ + o (1) and on U -we have m = -m ⋆ + o (1), while Φ β 1 ( m ) = Φ β 1 ( m ⋆ ) + o (1) in both neighborhoods. Therefore

<!-- formula-not-decoded -->

because the leading K Φ β 1 ( m ⋆ ) contributions cancel and the remaining cm term evaluates to ± cm ⋆ . Combining with (34) implies

<!-- formula-not-decoded -->

and thus M K ⇒ pδ m ⋆ +(1 -p ) δ -m ⋆ under Y = 1.

̸

We are now in the position to show that Bayes risk vanishes, as claimed in item (2). Pick any t with | m 0 | < t < m ⋆ and define ˜ g K ( J ) = 1 {| M K | ≥ t } . Under Y = 0, (32) implies | M K | < t with probability → 1. Under Y = 1, (34) implies | M K | > t with probability → 1. Therefore P(˜ g K = Y ) → 0, i.e. R (˜ g K ) → 0. Since g ⋆ K minimizes risk, R ( g ⋆ K ) ≤ R (˜ g K ) → 0.

Next, we move on to proving item (3). Under the CI model with marginals ( q 0 , q 1 ), the (oracle) CI log-likelihood ratio depends only on S K = ∑ K j =1 J j or equivalently s K = S K /K :

<!-- formula-not-decoded -->

Since q 1 > q 0 , the function of s in parentheses is strictly increasing and has a unique root s thr ∈ ( q 0 , q 1 ). Thus the CI-predictor satisfies (for all large K , ignoring the vanishing prior term at scale K )

<!-- formula-not-decoded -->

Under Y = 0, we have s K = (1 + M K ) / 2 → (1 + m 0 ) / 2 = q 0 < s thr in probability, so P( g ind K = 1 | Y = 0) → 0.

Under Y = 1, we have s K → (1 ± m ⋆ ) / 2 depending on the phase. By (8), the negative-phase limit (1 -m ⋆ ) / 2 is strictly smaller than q 0 < s thr , so g ind K → 0 on the negative phase; while (1 + m ⋆ ) / 2 > s thr so g ind K → 1 on the positive phase. Therefore

<!-- formula-not-decoded -->

and hence

<!-- formula-not-decoded -->

Together with R ( g ⋆ K ) → 0, this yields the claimed nonvanishing excess-risk lower bound.

## F Numerical Simulations

## F.1 CI Judges: Uniform vs. Weighted Majority Vote

We present sanity-check experiment in the conditionally independent (CI) setting, where the classical Dawid-Skene family is well-specified. Each item has a latent label Y i ∈ { 0 , 1 } and K = 6 judges produce independent votes J ij ∈ { 0 , 1 } conditional on Y i . Judge j is characterized by sensitivity α j = P( J ij = 1 | Y i = 1) and specificity β j = P( J ij = 0 | Y i = 0). For each setup we generate n = 200 items from the CI model with the true ( α, β ) listed in Table 2. We consider four setups spanning strong annotators (Setup 1) and heterogeneous, partially unreliable annotators (Setups 24). We evaluate two aggregation rules: (i) Uniform majority vote (Uniform MV), which predicts the class supported by a strict majority of votes, and (ii) Weighted majority vote learned by the EM approach in Algorithm 1, where we fit the asymmetric CI model with Beta priors on ( α j , β j ) and then apply the induced Bayes-optimal linear rule (equivalently, a weighted vote with weights given by the estimated log-odds contributions of each judge.

Table 3 reports average 0-1 accuracy across runs for each setup. Two trends are consistent with theory. First, when all judges are strong and roughly exchangeable (Setup 1), uniform MV is already near-optimal and EM-based weighting provides only a small gain. Second, in the heterogeneous regimes (Setups 2-4), uniform MV can substantially underperform because it treats all judges as equally informative and ignores asymmetric error patterns. In contrast, CI-WMV learns to

Table 2: True per-judge sensitivities and specificities used in the CI simulations ( K = 6 judges).

| | True sensitivities | True sensitivities | True sensitivities | True sensitivities | True sensitivities | True sensitivities | True specificities | True specificities | True specificities | True specificities | True specificities | True specificities |
|-------|----------------------|----------------------|----------------------|----------------------|----------------------|----------------------|----------------------|----------------------|----------------------|----------------------|----------------------|----------------------|
| Setup | α 1 | α 2 | α 3 | α 4 | α 5 | α 6 | β 1 | β 2 | β 3 | β 4 | β 5 | β 6 |
| #1 | 0.90 | 0.90 | 0.90 | 0.90 | 0.90 | 0.90 | 0.90 | 0.90 | 0.90 | 0.95 | 0.90 | 0.95 |
| #2 | 0.26 | 0.53 | 0.64 | 0.50 | 0.67 | 0.70 | 0.34 | 0.54 | 0.65 | 0.76 | 0.70 | 0.30 |
| #3 | 0.26 | 0.30 | 0.24 | 0.50 | 0.70 | 0.80 | 0.80 | 0.90 | 0.50 | 0.60 | 0.37 | 0.23 |
| #4 | 0.60 | 0.63 | 0.74 | 0.75 | 0.67 | 0.80 | 0.70 | 0.59 | 0.95 | 0.86 | 0.77 | 0.83 |

Table 3: Comparing Weighted Majority Vote (CI-WMV) where the weights are learned via EM and Uniform Majority Vote under Conditionally (CI-UMV) independent judges with parameters represented in Table 2. Reported numbers represent the average accuracy over 20 trials.

| Setup | CI-WMV (via EM) | CI-UMV |
|---------|-------------------|----------|
| #1 | 0.997 | 0.995 |
| #2 | 0.726 | 0.597 |
| #3 | 0.611 | 0.52 |
| #4 | 0.93 | 0.917 |

up-weight reliable judges and down-weight weak (or effectively adversarial) ones, yielding large improvements: in Setup 2 accuracy increases from 0.597 to 0.726, and in Setup 3 from 0.520 to 0.611. Even in Setup 4, where most judges are reasonably informative but still heterogeneous, CIWMVimproves over uniform MV (0.930 vs. 0.917). Overall, these CI experiments establish a strong baseline: when conditional independence holds, learned weighted aggregation offers meaningful gains over uniform majority vote whenever annotator quality is non-uniform, and it recovers nearceiling performance when all annotators are strong.

## F.2 Dependent Judges: Ising/Factor models vs. Weighted Majority Voting

We next evaluate aggregation under dependent judges, where the conditional-independence (CI) is misspecified. Across the experiments below, the goal is to compare a strong CI baseline,Weighted MV learned by EM under the asymmetric CI model-Class-dependent Ising with classspecific couplings and factor models. All methods are trained in an unsupervised manner using the generalized-EM framework (Algorithm 1); for Ising models we use pseudo-likelihood in the M-step and approximate class scores in the E-step.

Simulation Setup 1 (Illustrating Theorem 2). To empirically illustrate the Curie-Weiss separation with informative marginals, we generate synthetic vote vectors from the class-conditional Curie-Weiss model (7) and compare the CI-predictors g ind K to the dependence-aware (near-Bayes) rule ˜ g K ( J ) = 1 {| M K | ≥ t } suggested by the proof. We fix ( π, β 0 , h 0 ) with β 0 ∈ (0 , 1) and h 0 < 0, and vary the low-temperature parameters ( β 1 , c ) with β 1 > 1 and c > 0; for each pair we set h 1 ,K = c/K and compute m 0 and m ⋆ ( β 1 ) from the mean-field equations. We restrict to parameter settings satisfying the separation condition (8) and choose a threshold t ∈ ( | m 0 | , m ⋆ ) (e.g., t = ( | m 0 | + m ⋆ ) / 2). For each ( β 1 , c, K ) we sample n i.i.d. items: draw Y ∼ Bernoulli( π ), then draw spins X ∈ {± 1 } K from (7) (e.g., via Glauber dynamics with burn-in), and finally map to votes J j = ( X j +1) / 2. We evaluate (i) the empirical risk (denoted by ˆ R ) of ˜ g K (a proxy for Bayes, which should approach 0 as K grows) and (ii) the empirical risk of the oracle CI-predictor g ind K , which uses the true marginals q 0 , q 1 to form the naive-Bayes log-likelihood ratio in S K = ∑ j J j . The

results are shown in Figure 4. The plots, directly mirror the theorem's message: ̂ R (˜ g K ) rapidly decreases with K , while ̂ R ( g ind K ) approaches a positive constant that varies smoothly with ( β 1 , c ) through π (1 -p ).

̸

Simulation Setup 2 (Illustrating Theorem 3). To empirically illustrate the asymptotic separation under the exchangeable latent-factor model (21), we simulate votes from the generative process with fixed parameters ( π, a, b, λ, σ 2 Z ) and vary λ and/or σ 2 Z while increasing the number of judges K . For each run, we draw n independent items: sample Y i ∼ Bernoulli( π ) and Z i ∼ N (0 , σ 2 Z ), then draw votes J i 1 , . . . , J iK | ( Y i , Z i ) iid ∼ Bernoulli( p ( Y i , Z i )). We evaluate two plug-in aggregators based on the empirical vote fraction s iK = K -1 ∑ K j =1 J ij : the Bayes-optimal prediction rule g ⋆ ∞ ( J i ) = 1 { ℓ ⋆ ( s i ∞ ) ≥ 0 } (approximated by using s iK in place of s i ∞ ), and the CI-prediction rule g ind ∞ ( J i ) = 1 { ℓ ind ( s i ∞ ) ≥ 0 } (again approximated using s iK ), where q y = E Z [ p ( y, Z )] is computed numerically. To visualize the separation predicted by the theorem, we again plot in Figure 5: (i) the empirical risks R ( g ⋆ K ) and R ( g ind K ) versus K for different values of λ and σ 2 Z ), and (ii) the empirical separation. These plots highlight the theorem's message: under dependence (larger | λ | or σ 2 Z ), the disagreement event { g ind ∞ = g ⋆ ∞ } typically expands, and the separation becomes nonzero.

Figure 4: Ising predictors (Class-Dep. Ising) versus CI-predictors (CI-WMV): The plots on the left and right represent the empirical risk and empirical separation respectively. Top row corresponds to β 1 = 2 , c = 1 . 5. Bottom row corresponds to β 1 = 5 , c = 1. For all plots, π = 0 . 7 , β 0 = 0 . 5 , h 0 = -0 . 5 and n = 1000. The standard errors are of small width, although they are plotted.

<!-- image -->

Across both dependent judges cases-dependence induced by latent factors and dependence induced by Curie-Weiss interactions-CI based Weighted Majority Voting aggregation rule underperforms the respective posteriors.

Figure 5: Latent-factor (Factor) predictor versus CI-predictors (CI-WMV). The plots on the left and right represent the empirical risk and empirical separation respectively. Top row corresponds to | λ | = 0 . 1 , σ 2 Z = 1. Bottom row corresponds to | λ | = 0 . 15 , σ 2 Z = 1 . 5. For all plots, π = 0 . 7 , a = 0 . 5 , b = 1 and n = 1000. The standard errors are of small width, although they are plotted.

<!-- image -->

## G Additional Details on Real Datasets

## G.1 Preprocessing of WikiQA Dataset

In Tables 4 and 5, we present the examples of two questions from the WikiQA dataset along with the corresponding candidate answers. In the former case, there exists a correct answer among the candidate ones, therefore, we label a concatenated text chunk as relevant. In the latter case, none of the candidate answers is correct, therefore. we label a concatenated text chunk as irrelevant, meaning it does not contain information that can be directly used to answer the question at hand.

## G.2 Preprocessing of Jigsaw Unintended Bias in Toxicity Classification Dataset

We use the comments from the private leaderboard test set ( test private expanded.csv ). The original sample size is 97320. We reduce attention to the comments which had at least five annotators and which are at least 100 characters long. Subsequently, we group the comments into four buckets: \[0 , 0 . 25) , \[0 . 25 , 0 . 5) , \[0 . 5 , 0 . 75) , [0 . 75 , 1] based on the corresponding toxicity score, representing the fraction of annotators who marked a given comment as toxic. Finally, we select 1k comments from each bucket at random to form the final dataset. The ground-truth label is set to one (toxic) if and only if at least half of annotators marked the comment as toxic.

## G.3 Prompts

In this Section, we describe the prompt templates that were used for LLM-as-a-judge evaluations:

1. The template for relevance evaluation is provided in Figure 6.

Table 4: Candidate answers for question Q1686 : 'Who plays dumbledore in harry potter 6' in WikiQA dataset. In this example, a correct answer is present among the candidate answers, therefore the text sample obtained by concatenation is labeled as relevant.

| Candidate Answer | Label |
|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|
| Professor Albus Percival Wulfric Brian Dumbledore is a major character and protagonist of J. K. Rowling's Harry Potter series. | 0 |
| For most of the series, he is the headmaster of the wizarding school Hogwarts. | 0 |
| As part of his backstory, it is revealed that he is the founder and leader of the Order of the Phoenix, an organisation dedicated to fighting the main antagonist of the series, Lord Voldemort. | 0 |
| Dumbledore is portrayed by Richard Harris in the film adaptions of Harry Potter and the Philosopher's Stone and Harry Potter and the Chamber of Secrets. | 0 |
| After Harris' death, Michael Gambon portrayed Dumbledore for all of the remaining films. | 1 |
| Rowling stated she chose the name Dumbledore, which is an Early Modern English word for 'bumblebee', because of Dumbledore's love of music: she imagined him walking around 'humming to himself a lot'. | 0 |

Table 5: Candidate answers for question Q2943 : 'What is the average wear time for braces?' in WikiQA dataset. In this example, a correct answer is not present among the candidate answers, therefore the text sample obtained by concatenation is labeled as irrelevant.

| Candidate Answer | Label |
|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|
| A patient with braces. | 0 |
| Dental braces (also known as orthodontic braces, or braces) are devices used in orthodontics that align and straighten teeth and help to position them with regard to a person's bite, while also working to improve dental health. | 0 |
| They are often used to correct underbites, as well as malocclusions, overbites, cross bites, open bites, deep bites, crooked teeth, and various other flaws of the teeth and jaw. | 0 |
| Braces can be either cosmetic or structural. | 0 |
| Dental braces are often used in conjunction with other orthodontic appliances to help widen the palate or jaws and to otherwise assist in shaping the teeth and jaws. | 0 |

2. The template for toxicity evaluation is provided in Figure 7.
1. The template for summarization evaluation is provided in Figure 8.

```
You are comparing a reference text to a question and trying to determine if the reference text contains information relevant to answering the question. Here is the data: [BEGIN DATA] ************ [Question]: {query} ************ [Reference text]: {reference} [END DATA] Compare the Question above to the Reference text. You must determine whether the Reference text contains information that can answer the Question. Please focus on whether the very specific question can be answered by the information in the Reference text. Your response must be structured in XML format with special characters properly escaped. The parent tag must be 'response' and must have two child fields: -reasoning: step by step reasoning for your evaluation. -score: only respond with "True" or "False". Response with "True" if you think the reference text contains an answer to the Question. Respond with "False" if you think the reference text does not contain an answer to the Question. Strictly follow the response format instructions: <response> <reasoning>Your step by step reasoning</reasoning> <score>The final score</score> </response> For example, your response could look like (only use the below as a formatting example): <response> <reasoning>Your step by step reasoning for evaluating readability</reasoning> <score>True</score> </response>
```

Figure 6: Prompt template for evaluating text relevance. We adopt Arize Phoenix evaluation template with minor changes applied to LLMaaJ response format.

Figure 7: Prompt template for evaluating text toxicity. We adopt Arize Phoenix toxicity template with minor changes applied to LLMaaJ response format.

<!-- image -->

```
You are comparing the summary text and it's original document and trying to determine if the summary is good. Here is the data: [BEGIN DATA] ************ [Summary]: {output} ************ [Original Document]: {input} [END DATA] Compare the Summary above to the Original Document and determine if the Summary is comprehensive, concise, coherent, and independent relative to the Original Document. Your response must be either True or False. "False" means that the Summary is not comprehensive, concise, coherent, and independent relative to the Original Document. "True" means the Summary is comprehensive, concise, coherent, and independent relative to the Original Document. Your response must be structured in XML format with special characters properly escaped. The parent tag must be 'response' and must have two child fields: -reasoning: step by step reasoning for your evaluation. -score: only respond with "True" or "False". Response with "True" if you think the Summary is comprehensive, concise, coherent, and independent relative to the Original Document. Respond with "False" if you think otherwise. Strictly follow the response format instructions: <response> <reasoning>Your step by step reasoning</reasoning> <score>The final score</score> </response> For example, your response could look like (only use the below as a formatting example): <response> <reasoning>Your step by step reasoning for evaluating the summary</reasoning> <score>True</score> </response>
```

Figure 8: Prompt template for evaluating text summarization. We adopt Arize Phoenix evaluation template with minor changes applied to LLMaaJ response format.
