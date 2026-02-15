### **The Alternative Annotator Test for LLM-as-a-Judge:** **How to Statistically Justify Replacing Human Annotators with LLMs**

**Nitay Calderon** _[T]_ **Roi Reichart** _[T]_

**Rotem Dror** _[H]_

_T_ Faculty of Data and Decision Science, Technion
_H_ Department of Information Systems, University of Haifa
nitay@campus.technion.ac.il roiri@technion.ac.il rdror@is.haifa.ac.il

**Abstract**

The “LLM-as-an-annotator” and “LLM-as-ajudge” paradigms employ Large Language
Models (LLMs) as annotators, judges, and evaluators in tasks traditionally performed by humans. LLM annotations are widely used, not
only in NLP research but also in fields like
medicine, psychology, and social science. Despite their role in shaping study results and
insights, there is no standard or rigorous procedure to determine whether LLMs can replace
human annotators. In this paper, we propose
a novel statistical procedure, the Alternative
Annotator Test (alt-test), that requires only a
modest subset of annotated examples to justify
using LLM annotations. Additionally, we introduce a versatile and interpretable measure
for comparing LLM annotators and judges. To
demonstrate our procedure, we curated a diverse collection of ten datasets, consisting of
language and vision-language tasks, and conducted experiments with six LLMs and four
prompting techniques. Our results show that
LLMs can sometimes replace humans with
closed-source LLMs (such as GPT-4o), outperforming the open-source LLMs we examine,
and that prompting techniques yield judges of
varying quality. We hope this study encourages
more rigorous and reliable practices. [1]

**1** **Introduction**

The rise of Large Language Models (LLMs) has
transformed the field of Natural Language Processing (NLP), bringing unprecedented capabilities in
reasoning and generating human-like text (Kojima
et al., 2022; Achiam et al., 2023; Laskar et al.,
2023; Yang et al., 2024). Recently, a new trend
has emerged where LLMs are employed as annotators and judges across various NLP applications
(Li et al., 2024a; Tan et al., 2024b).

1Code for the procedure and datasets are available at:
[https://github.com/nitaytech/AltTest](https://github.com/nitaytech/AltTest)

One key advantage of LLM-as-an-annotator and
LLM-as-a-judge [2] paradigms is the scalability and
speed of LLMs. They can quickly annotate largescale datasets, reducing the time required for tasks
traditionally performed by costly human annotators
(Nasution and Onan, 2024). LLMs also avoid challenges inherent to human factors, such as fatigue
and guideline misinterpretation (Uma et al., 2021;
Bartsch et al., 2023). In certain cases, they even
outperform crowd-workers (Gilardi et al., 2023;
Nahum et al., 2024).
Indeed, LLMs-as-judges are extensively used in
research, taking on a pivotal role once filled by humans. They are employed to annotate new datasets
(Gat et al., 2024; Tan et al., 2024b), or refine existing ones (Nahum et al., 2024; Pavlovic and Poesio,
2024), and commonly serve as evaluators for benchmarking models and methods (Ahmed et al., 2024;
Gu et al., 2024; Li et al., 2024a).
LLMs’ influence extends far beyond the NLP
field. They annotate papers for literature reviews
(Calderon and Reichart, 2024; Joos et al., 2024) or
extract findings from academic literature (Khraisha
et al., 2024; Naik et al., 2024). They are also utilized in cognitive sciences to simulate human subjects (Aher et al., 2023; Shapira et al., 2024; Trott,
2024\) and in social science, researchers leverage
LLM annotations to uncover social and cultural
insights (Ventura et al., 2023; Ziems et al., 2024).
Accordingly, LLMs directly shape the results, findings, and insights of studies and guide the direction
of scientific inquiry, prioritization, and innovation.
Despite the advantages of the LLM-as-a-judge
paradigm, research shows that LLMs amplify biases, leading to unfair or inconsistent judgments

2The term “LLM-as-a-judge” typically refers to LLMs
evaluating outputs of other LLMs. It can be viewed as a
special case of the broader “LLM-as-an-annotator” paradigm.
However, since “LLM-as-a-judge” is more widely used, we
adopt it throughout this work to refer more generally to any
evaluation, annotation, or labeling of texts (or images) traditionally performed by humans, regardless of the input source.

16051

_Proceedings of the 63rd Annual Meeting of the Association for Computational Linguistics (Volume 1:_ _Long Papers)_, pages 16051–16081
July 27 - August 1, 2025 ©2025 Association for Computational Linguistics

(Ashktorab et al., 2024; Chen et al., 2024c; Ye et al.,
2024\) and that they may struggle with tasks that
require deep contextual understanding or domainspecific expertise (Ravid and Dror, 2023; Szymanski et al., 2024). These weaknesses highlight the
need for rigorous evaluation and transparency when
relying on LLM annotations in research.
Yet, many studies employing LLM annotations
do not explicitly measure the alignment between
LLMs and humans, and those that do typically
use traditional measures such as accuracy (%
agreements), F1 score, Inter-Annotator-Agreement
(IAA) kappas, and correlation (Li et al., 2024b),
which have limitations. To start, IAA measures assess agreement among a group of annotators, while
we aim to compare the LLM to the group. Other
measures frequently rely on majority vote labels,
overlooking important nuances that individuals introduce. Moreover, there are no established criteria
for making a definitive yes/no decision on whether
an LLM can replace humans (e.g., _“is an F1 score_
_of 0.6 sufficient?”_ ). This decision demands statistical rigor, which often lacks in the way researchers
apply traditional measures. Finally, they can only
evaluate whether an LLM _matches_ human performance (i.e., is bounded by it) but cannot determine
whether it provides a _better_ alternative.
We argue that to justify using an LLM instead
of human annotators, researchers should demonstrate that _the_ _LLM_ _offers_ _a_ _better_ _alternative_ _to_
_recruiting human annotators._ In other words, when
factoring in the cost-benefit and efficiency advantages of LLM annotations, they should be as good
as or better than human annotations. In this paper, we propose a statistical procedure to verify
this claim, which we call _the Alternative Annotator_
_Test_, or simply _alt-test_ . This procedure is simple
and requires minimal effort to apply; it involves
comparing the LLM to a small group of human
annotators (at least three) on a modest subset of
examples (between 50 and 100). Our procedure is
described in §3 and illustrated in Figure 1. Once
applied, researchers can confidently rely on the
LLM’s annotations for their work.
In addition, we define a measure for comparing
LLM judges called the _Average Advantage Proba-_
_bility_ . This measure is naturally derived from our
statistical procedure and represents the probability
that the LLM annotations are as good as or better
(e.g., by being closer to the majority) than those of
a randomly chosen human annotator. It possesses
desirable properties that traditional measures lack

while maintaining a high correlation with them. It
is versatile, supports different types of annotations,
and is highly interpretable.
We exemplify the application of our procedure
with six LLMs and four prompting techniques.
To this end, we curate a diverse collection of ten
datasets, each with instances annotated by multiple
annotators. Our datasets vary in size, annotation
types (discrete, continuous, and free-text), number of annotators (3 to 13), and levels of annotator
expertise (crowd-workers, skilled annotators, and
experts). They encompass a wide range of language
tasks, including two vision-language tasks.
Our results indicate that in many cases, LLMs
can serve as an alternative to human annotators. Specifically, on nine datasets, at least one
LLM, with some prompting technique, successfully passed the alt-test. We found that closedsource LLMs (such as GPT-4o and Gemini-1.5)
consistently outperform open-source models we
examined (like Mistral-v3 and Llama-3.1), and that
in-context learning generally improves LLM performance, while chain-of-thought and ensemble
methods do not yield similar benefits.
Finally, in Appendix C, we propose modifications to our procedure to address advanced scenarios: handling imbalanced labels (§C.1), benchmarking against a single expert (§C.2), incorporating annotator quality scores (§C.3), and respecting
minority opinions in subjective tasks (§C.4).
Our contributions are as follows: (1) We propose a statistical procedure, the alt-test, to justify
replacing human annotators with LLMs; (2) We
introduce a versatile and interpretable measure, the
average advantage probability, for comparing LLM
judges; (3) We curate a diverse collection of ten
datasets and analyze six LLMs and four prompting
techniques, demonstrating that LLMs can sometimes replace humans; (4) We develop a theorem
regarding the optimal LLM-as-a-judge (§3.4, §D).
We encourage researchers to adopt our procedure and hope this study paves the way for rigorous
scientific practices in NLP and beyond.

**2** **Previous Work**

Research on LLMs as annotators and judges is a
rapidly growing field (Chiang et al., 2023; Zheng
et al., 2024a), resulting in numerous surveys (Gu
et al., 2024; Li et al., 2024a; Tan et al., 2024b;
Pavlovic and Poesio, 2024). Most studies focus on
enhancing LLM performance, either by parameter

16052

tuning (Gekhman et al., 2023; Yue et al., 2023;
Zhu et al., 2023; Jiang et al., 2024; Kim et al.,
2024\) or prompting strategies (Bai et al., 2023;
Moniri et al., 2024; Song et al., 2024). For instance,
Dong et al. (2024) investigated personalized LLM
judges, Verga et al. (2024) proposed using a panel
of diverse LLMs, and Chen et al. (2024b) extended
LLM-as-a-judge to multimodal tasks.
Many statistical works propose corrections to
estimations that are built with LLM annotations
(Angelopoulos et al., 2023a; Egami et al., 2023;
Angelopoulos et al., 2023b; Chatzi et al., 2024;
Gligoric et al., 2024; Ludwig et al., 2024). Conversely, the question we address is how to justify
replacing human annotators with LLMs, ensuring
researchers can confidently apply LLMs for model
evaluation or data annotation.
While existing works do not directly address how
to justify human replacement, many have explored
how well LLMs align with human annotators (Chiang and Lee, 2023; Ahmed et al., 2024; Bavaresco
et al., 2024; Chen et al., 2024a; Gera et al., 2024;
Lambert et al., 2024; Nahum et al., 2024; Nasution
and Onan, 2024; Tan et al., 2024a; Trott, 2024), often focusing on specific LLM limitations or biases
(Wu and Aji, 2023; Ashktorab et al., 2024; Jung
et al., 2024; Chen et al., 2024c; Wang et al., 2024;
Xu et al., 2024). These studies rely on traditional
measures such as accuracy, F1 score, correlation,
or metrics that quantify bias. In contrast, we propose a statistical procedure to determine whether
an LLM can be used, providing a clear yes/no answer. Additionally, we introduce an interpretable
and versatile measure for comparing LLM judges.

**3** **Method**

We propose using an LLM-as-a-judge instead of
human annotators when it offers a comparable alternative to recruiting an annotator. By comparing
the predictions of the LLM to those of humans,
we can evaluate which more closely emulates the
gold label distribution. Gold labels represent the
“true” or ground truth annotations and are typically
determined through rigorous processes, such as
consensus among experts or extensive quality control. Consequently, since experts are expensive
and often inaccessible, we assume gold labels are
unavailable. Hence, a common approach is to approximate them using the collective responses of
multiple annotators. This is the exact setup we use
in this paper: a modest subset of randomly sampled

Figure 1: **An** **Illustration** **of** **the** **Alt-Test:** Given instances annotated by human annotators, we first exclude
each annotator in turn to estimate the probabilities that
the LLM better represents the remaining annotators and
that the excluded annotator better represents them. We
then test whether the LLM probability exceeds the annotator probability (considering a cost-benefit penalty
_ε_ ), and apply a False Discovery Rate (FDR) controlling
procedure. Then, we calculate the winning rate, _ω_, as
the proportion of rejected hypotheses. If _ω_ _≥_ 0 _._ 5, we
conclude that the LLM is more likely to hold an advantage over human annotators, which justifies using it.

examples, each annotated by multiple annotators. [3]

Accordingly, a key consideration in our method
is that the perspective of every annotator is valued.
Specifically, our leave-one-out approach excludes
one annotator at a time and evaluates how well the
LLM’s annotations align with those of the remaining annotators. Similarly, we evaluate the alignment of the excluded annotator with the remaining
annotators. We then compare the LLM and the
excluded annotator, justifying the use of the LLMas-a-judge if _the LLM aligns more closely with the_
_collective distribution than an individual does_ . The
procedure is illustrated in Figure 1.

**Notations** **and** **Definitions** For a dataset of _n_
instances _x_ 1 _, . . ., xn_ and _m_ human annotators
_{_ _}_
_h_ 1 _, . . ., hm_, we denote the annotation of the
_{_ _}_
_j_ th annotator for instance _xi_ as _hj_ ( _xi_ ). The

3In §B.2, we discuss the number of annotators, their profiles, and levels of expertise to ensure reliable outcomes.

16053

annotation predicted by the LLM is denoted as
_f_ ( _xi_ ). In addition, \[ _j_ \] represents the set of in
_−_
dices from 1 to _m_ excluding the _j_ th index, i.e.,

\[ _−j_ \] = _{_ 1 _, . . ., j_ _−_ 1 _, j_ + 1 _, . . ., m}_ . The set of
indices of the instances annotated by _hj_ is denoted
as I _j_ . Similarly, H _i_ is the set of indices of human annotators that annotated _xi_ . For example, assume we have three instances and four annotators.
I2 = _{_ 2 _,_ 3 _}_ means that the second annotator, _h_ 2,
annotated instances _x_ 2 and _x_ 3, and H1 = _{_ 1 _,_ 3 _,_ 4 _}_
means that the first instance, _x_ 1, was annotated by
the first, third, and fourth annotators, _h_ 1 _, h_ 3 _, h_ 4.

**3.1** **Computing the Instance Alignment Score**

We start by examining the removal of each human
annotator _hj_ in turn and compute a score that measures the alignment between the annotations of the

\[ _−j_ \] human annotators and the annotation of the
LLM for instance _xi_ . We use _S_ ( _f, xi, j_ ) to denote
the _alignment scoring function_ between _f_ ( _xi_ ) and
the annotations of H _i_ \[ _−j_ \]. For example, _S_ could be
RMSE (root mean squared error) in regression tasks
(continuous numerical labels) or ACC (accuracy) in
classification tasks (categorical or rank labels).
In generation tasks (e.g., machine translation),
_S_ can be computed using a relevant evaluation
metric (denoted as sim) that typically measures
the similarity between the LLM-generated output
and the human-generated output. For convenience,
we assume that higher values of _S_ indicate a
better alignment between an LLM and the human
annotators; thus, we use negative RMSE. Below,
we formally define the mentioned variants of _S_ :

tor will be constructed by calculating the percentage of instances for which the score of the LLM,
_S_ ( _f, xi, j_ ), was higher or equal to the score of the
_j_ th excluded human annotator, _S_ ( _hj, xi, j_ ). We
represent this event (for _xi_ ) using the indicator:

_Wi,j_ _[f]_ [=]

1 _,_ if _S_ ( _f, xi, j_ ) _S_ ( _hj, xi, j_ )
_≥_
0 _,_ otherwise

Similarly, we define the indicator _Wi,j_ _[h]_ [by revers-]
ing the inequality (to _≤_ ) in the definition above,
representing that the annotation of _hj_ for _xi_ is comparable to that of the LLM.
The expectation of _Wi,j_ _[f]_ [represents] [the] [proba-]
bility that the LLM annotations are as good as or
better than those of _hj_ . We estimate this probability
by averaging _Wi,j_ _[f]_ [values across all instances:]

1
_ρ_ _[f]_ _j_ [=] [P][ˆ][(][LLM] _[ ⪰]_ _[h][j]_ [) =] [E][ˆ]\[[] _[W][ f]_ _i,j_ [] =\]
_|_ I _j|_

_Wi,j_ _[f]_
_i∈_ I _j_

~~�~~

~~�~~

```
- 1
```

RMSE( _f, xi, j_ ) =
_−_ _−_ _|_ H _i| −_ 1

( _f_ ( _xi_ ) _hk_ ( _xi_ )) [2]
_−_
_k∈_ H _i_ \[ _−j_ \]

We denote this estimation of the _advantage over hj_
_probability_ as _ρ_ _[f]_ _j_ [.] [Similarly,] _[ ρ][h]_ _j_ [estimates the prob-]
ability that _hj_ holds an advantage over the LLM,
calculated by averaging the values of _Wi,j_ _[h]_ [.] [The set]

_{_ ( _ρ_ _[f]_ _j_ _[, ρ]_ _j_ _[h]_ [)] _[}]_ _j_ _[m]_ =1 [is used in our statistical procedure.]

**3.3** **Should the LLM Replace Annotators?**

Using an LLM instead of a human annotator is
justified if the LLM offers a reliable alternative to
hiring an annotator. To formalize this, if _ρ_ _[f]_ _j_ [is] **[ sig-]**
**nificantly** larger than _ρ_ _[h]_ _j_ [it indicates that employing]
the LLM instead of _hj_ is a _justified evidence-based_
_decision_ . Notice, however, that employing an LLM
is a cheaper and less labor-intensive alternative.
Therefore, we introduce _ε_, [4] a _cost-benefit_ _hyper-_
_parameter_ which penalizes _ρ_ _[h]_ _j_ [to reflect the higher]
cost and effort associated with human annotation.
We define the following set of hypothesis testing
problems to test if the LLMs’ relative advantage
probability is significantly larger than that of _hj_ :

**H0j** : _ρ_ _[f]_ _j_ _[≤]_ _[ρ]_ _j_ _[h]_ _[−]_ _[ε]_ vs. **H1j** : _ρ_ _[f]_ _j_ _[> ρ]_ _j_ _[h]_ _[−]_ _[ε]_

The appropriate statistical test for this hypothesis
problem is a paired _t_ -test (Dror et al., 2018), which
examines the difference between the _i_ th indicators:
_dd_ ¯ _i,jj_ == _ρ W_ _[h]_ _j_ _[−]_ _i,j_ _[h]_ _[−][ρ]_ _j_ _[f][W]_ [is greater than or equal to] _[ f]_ _i,j_ [. The null hypothesis asserts that] _[ ε]_ [, while]
the alternative hypothesis posits that it is smaller.

4In §B.1 we explore how different _ε_ values impact our
procedure and recommend suitable ones for researchers.

1
ACC( _f, xi, j_ ) =
_|_ H _i| −_ 1

1
SIM( _f, xi, j_ ) =
_|_ H _i| −_ 1

**1** _f_ ( _xi_ ) = _hk_ ( _xi_ )
_{_ _}_
_k∈_ H _i_ \[ _−j_ \]

sim( _f_ ( _xi_ ) _, hk_ ( _xi_ ))
_k∈_ H _i_ \[ _−j_ \]

Note that RMSE( _hj, xi, j_ ), ACC( _hj, xi, j_ ), and

_−_
SIM( _hj, xi, j_ ) represent score differences between
_hj_ and the other annotators. Consequently, we are
interested in comparing _S_ ( _f, xi, j_ ) to _S_ ( _hj, xi, j_ ).

**3.2** **Estimating the Advantage Probabilities**

After computing the alignment score for each instance, we estimate the likelihood that the LLM
achieves a comparable alignment with the annotators to that of the excluded annotator. The estima

16054

The test statistic _tj_ is defined as:

_d_ ¯ _j_ _ε_
_tj_ = _−_ _sj_ =
_sj/_ ~~_[√]_~~ _n_

~~��~~ _ni_ =1 ~~�~~ _di,j_ _dj_ ~~�~~ 2

_−_ [¯]

_n −_ 1

The p-value can be calculated using a student’s _t_ distribution table. When _n_ _\<_ 30, the normality
assumption may not hold, and a non-parametric
test (e.g., Wilcoxon signed-rank) should be used.
If the p-value _< α_ (typically _α_ = 0 _._ 05), we reject
the null hypothesis, concluding that _the LLM holds_
_a statistically significant advantage over hj_ _when_
_considering the cost-benefit tradeoff._
So far, we discussed the advantage of LLMs
over a single human annotator. To generalize
our conclusion to any annotator, we measure the
percentage of annotators that the LLM “wins”,
i.e., the proportion of rejected null hypotheses.
We denote this _winning rate (WR)_ by _ω_, formally:

_ω_ = [1]

_m_

- _m_

**1** _H_ 0 _j_ is rejected
_{_ _}_
_j_ =1

where **1** _H_ 0 _j_ is rejected is an indicator that re\_{\_ _}_
ceive one if the null hypothesis is rejected and
zero, otherwise. If _ω_ _≥_ 0 _._ 5, [5] then the LLM wins
the majority of human annotators, hence _we assert_
_that it can replace human annotators._

**Multiple** **Comparison** **Correction** Simply
counting the number of rejected null hypotheses
is problematic due to the accumulation of Type-I
errors when performing multiple hypothesis tests,
particularly when the hypotheses are dependent
(Dror et al., 2017). In our case, the dependency
arises because the score of _hj_ relies on the
annotations of the remaining \[ _−j_ \] annotators (see
how _S_ is defined). The standard practice to address
this issue is a multiple comparison correction.
We suggest using a procedure that controls the
false discovery rate (FDR), which is the expected
proportion of false positives (incorrect rejections
of null hypotheses) among all rejected hypotheses
in a multiple-hypothesis testing scenario. In other
words, the FDR-controlling procedure ensures that
the observed WR _ω_ is reliable and does not overestimate the true percentage of wins due to accumulated false rejections or dependence between
hypotheses. We recommend using the BenjaminiYekutieli (BY) procedure (Benjamini and Yekutieli

5This is a hyperparameter. It is set to 0.5 to establish that it
is _more likely_ that the LLM holds an advantage over humans.
Stricter thresholds can be used in high-stakes domains.

(2001), see Algorithm 1 in the Appendix) to control
the FDR, as it is specifically suited for scenarios
where the null hypotheses are dependent. In our
experiments, we use the standard target FDR level
of _q_ = 0 _._ 05 (i.e., in expectation, at most 5% of the
rejections will be false rejections).

**Summary:** **the** **Alt-Test** As illustrated in Figure 1, the alt-test involves the following steps: First,
we compute the set of probabilities _{_ ( _ρ_ _[f]_ _j_ _[, ρ]_ _j_ _[h]_ [)] _[}]_ _j_ _[m]_ =1 [,]
where each _ρj_ represents the advantage of the LLM
over _hj_ and vice versa. Next, we conduct _m_ onesample proportion t-tests for the difference _ρ_ _[h]_ _j_ _j_
against _ε_, resulting in a corresponding set of _[−]_ _[ρ]_ _m_ _[f]_
p-values. We then apply the BY procedure to these
p-values, which identifies the set of rejected null hypotheses. Finally, we compute the winning rate (the
proportion of rejected hypotheses) and if _ω_ _≥_ 0 _._ 5,
we can statistically justify using LLM annotations.

**3.4** **How to Compare LLM Judges?**

In many scenarios, we wish to compare different
LLM judges. While it is possible to compare LLMs
by their winning rate ( _ω_ ), we argue this is suboptimal. First, _ω_ does not account for the magnitude
of the wins. For example, _ρ_ _[f]_ _j_ [= 0] _[.]_ [9][ and] _[ ρ]_ _j_ _[f]_ [= 0] _[.]_ [6]
contribute equally to _ω_ if their respective null hypotheses are rejected. Second, _ω_ depends on the
value of _ε_, and third, the range of its possible values depends on the number of human annotators,
making it a coarse measure. For instance, with only
three annotators, _ω_ value is limited to 0, [1] ⁄3, [2] ⁄3, 1.
Therefore, for comparing LLM judges, we propose the _Average Advantage Probability (AP)_ :

We argue that _ρ_ is a good measure for comparing
LLM judges due to its desirable properties. Unlike
_ω_, _ρ_ spans a denser range of values and accounts
for the magnitude of _ρ_ _[f]_ _j_ [s.] [Furthermore, it is more]
interpretable than traditional measures like F1, Cohen’s _κ_, or correlation — it directly represents the
probability that the LLM annotations are as good
as or better than those of a randomly chosen annotator. This intuitive interpretation makes it accessible
and meaningful for decision-makers. Finally, _ρ_
can be applied consistently across different types
of annotation tasks (discrete, continues, and freetext), providing a unified evaluation framework that
eliminates the need to switch between measures.

_ρ_ = [1]

_m_

- _m_

_ρ_ _[f]_ _j_
_j_ =1

16055

**Discrete Annotation Tasks**

|Dataset|m n Cats I.p.A A.p.I|Agree Fleiss’s κ|Task Description|
|---|---|---|---|
|WAX<br>LGBTeen<br>MT-Bench<br>Framing<br>CEBaB-A|8 C<br>246<br>16<br>172<br>5.61<br>4 E<br>880<br>5<br>640<br>2.91<br>3 E<br>120<br>3<br>82<br>2.05<br>4 S<br>2552<br>3<br>1914<br>3.00<br>10 C<br>1008<br>3<br>403<br>4.00|0.33<br>0.26<br>0.69<br>0.53<br>0.66<br>0.49<br>0.79<br>0.57<br>0.86<br>0.74|Identify the type of relationship between two associated words.<br>Assess the emotional support provided by LLMs to queer youth.<br>Compare two conversations between a user and different LLMs.<br>Annotate climate articles with frame-related yes/no questions.<br>Determine the sentiment for four aspects of restaurant reviews.|

**Continuous Annotation Tasks**

|Dataset|Anns Items Scale I.p.A A.p.I|MAE Pearson|Task Description|
|---|---|---|---|
|SummEval<br>10k Prompts<br>CEBaB-S<br>Lesion|3 E<br>6400<br>1–5<br>6400<br>3.00<br>13 S<br>1698<br>1–5<br>296<br>2.26<br>10 C<br>711<br>1–5<br>219<br>3.08<br>6 S<br>500<br>1–6<br>497<br>5.96|0.51<br>0.74<br>0.84<br>0.41<br>0.67<br>0.67<br>0.44<br>0.77|Rate model-generated summaries on four aspects.<br>Rate the quality of synthetic and human-written prompts.<br>Identify the star rating (1-5) given in restaurant reviews.<br>Score fve melanoma-related features based on lesion images.|

**Free-Text Annotation Tasks**

|Dataset|Anns Items – I.p.A A.p.I|Avg. Similarity|Task Description|
|---|---|---|---|
|KiloGram|50 C<br>993<br>–<br>144<br>7.27|0.28|Generate free-text descriptions of tangram images.|

Table 1: **Details of the Ten Datasets:** The number of human annotators ( _m_ ), data instances ( _n_ ), and categories
(Cats). The letter in the ‘ _m_ ’ column indicates the type of annotators: Experts (E), Skilled (S), or Crowd-workers
(C). I.p.A and A.p.I denote the average numbers of items per annotator and annotators per item, respectively. For
discrete tasks, we compute the proportion of pairwise agreements between human annotators (Agree) and Fleiss’s _κ_ .
For continuous tasks, we compute the mean absolute error between annotators (MAE) and the average Pearson
correlation. For the text generation task, we compute the average embedding cosine similarity (see Table 4).

**The Optimal LLM-as-a-Judge** We now turn to
the question of what constitutes the optimal LLMas-a-judge. We define it as an LLM that achieves
an advantage probability of _ρ_ = 1 (since _ω_ depends
on _n_ and _ε_, we do not include it in the theorem).
The optimal LLM-as-a-judge naturally depends on
the choice of the scoring function, _S_ ( _f, xi, j_ ). The
theorem below addresses two functions: ACC (for
discrete tasks) and _−_ RMSE (for continuous tasks).
See Appendix D for more details and the proof.

**Theorem** **1** (Optimal LLM-as-a-Judge) **.** _For_ _a_
_given dataset, let S_ ( _f, xi, j_ ) _be the alignment scor-_
_ing function. The optimal LLM-as-a-judge, denoted_
_as f_ _[∗]_ ( _xi_ ) _, is defined as follows:_

- _If S_ = ACC _, then f_ _[∗]_ ( _xi_ ) = _MV_ ( _xi_ ) _, predict-_
  _ing the majority vote of the annotators for xi._

- _If_ _S_ = RMSE _,_ _then_ _f_ _[∗]_ ( _xi_ ) =

_−_

_k∈_ H _i_ _[h][k]_ [(] _[x][i]_ [)]

_If_ _S_ = RMSE _,_ _then_ _f_ _[∗]_ ( _xi_ ) = _k∈_ HH _i_ _i_ _[k]_ _[i]_ _,_

_−_ _|_ _|_

_predicting the mean annotation for xi._

agreement measures. We comprehensively review
each of the ten datasets in Appendix E.
The datasets span a broad range of tasks, including traditional NLP tasks like sentiment analysis,
word-relation labeling, and summarization evaluation, as well as modern LLM-related tasks like
conversation comparison, prompt quality assessment, and emotional support evaluation. Moreover,
two datasets address vision-language tasks: skin
lesion examination and abstract visual reasoning.
The selection of the datasets followed three principles: (1) covering diverse annotation types, including discrete, continuous, and free-text; (2) ensuring annotators have identifiers; and (3) requiring
each item be annotated by multiple annotators.

**4.2** **LLMs**

The six models that were used as candidate LLM
annotators for our experiments are _Gemini-1.5-_
_Flash and Pro_ [6] by Google DeepMind, _GPT-4o and_
_GPT-4o-mini_ [7] by Open AI, _Llama-3.1-7B-Instruct_ [8]

by Meta AI, and _Mistral-7B-Instruct-v0.3_ [9] by Mistral AI. Llama-3.1 and Mistral-v3 do not have results on Lesion and KiloGram datasets because they
are not able to process images. The prompts used
in our experiments are detailed in Appendix G, and,

[6https://deepmind.google/technologies/gemini/](https://deepmind.google/technologies/gemini/)
[7https://openai.com/index/hello-gpt-4o/](https://openai.com/index/hello-gpt-4o/)
[8https://www.llama.com/docs/](https://www.llama.com/docs/model-cards-and-prompt-formats/llama3_1/)
[model-cards-and-prompt-formats/llama3_1/](https://www.llama.com/docs/model-cards-and-prompt-formats/llama3_1/)

[9https://writingmate.ai/blog/](https://writingmate.ai/blog/mistral-7b-v03-guide-and-details)
[mistral-7b-v03-guide-and-details](https://writingmate.ai/blog/mistral-7b-v03-guide-and-details)

_In_ _both_ _cases,_ _the_ _optimal_ _LLM-as-a-judge_
_achieves an advantage probability of ρ_ = 1 _._

**4** **Experimental Setup**

**4.1** **Datasets**

We conducted experiments on ten diverse datasets,
varying in size, number of human annotators, and
types of annotators (crowd-workers, skilled annotators, or experts). Table 1 provides information about these datasets, including inter-annotator

16056

**Discrete Annotation Tasks**

|Col1|WAX (ε = 0.1)|LGBTeen (ε = 0.2)|MT-Bench (ε = 0.2)|Framing (ε = 0.15)|CEBaB-A (ε = 0.1)|
|---|---|---|---|---|---|
|Gemini-Flash<br>Gemini-Pro<br>GPT-4o<br>GPT-4o-mini<br>Llama-3.1<br>Mistral-v3|Acc<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.38<br>0.38<br>0.69<br>0.39<br>0.5<br>**0.74**<br>0.38<br>0.5<br>0.73<br>0.24<br>0.0<br>0.59<br>0.24<br>0.0<br>0.57<br>0.17<br>0.0<br>0.50|Acc<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.54<br>0.25<br>0.71<br>0.47<br>0.0<br>0.67<br>0.63<br>0.75<br>**0.77**<br>0.59<br>0.75<br>0.76<br>0.54<br>0.0<br>0.72<br>0.58<br>0.25<br>0.75|Acc<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.62<br>0.0<br>0.72<br>0.62<br>0.0<br>0.76<br>0.68<br>0.0<br>**0.77**<br>0.60<br>0.0<br>0.74<br>0.54<br>0.0<br>0.69<br>0.52<br>0.0<br>0.68|Acc<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.69<br>1.0<br>0.83<br>0.79<br>1.0<br>0.91<br>0.80<br>1.0<br>**0.92**<br>0.74<br>1.0<br>0.87<br>0.66<br>0.5<br>0.80<br>0.66<br>0.25<br>0.80|Acc<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.88<br>0.7<br>0.91<br>0.91<br>0.9<br>**0.94**<br>0.90<br>0.9<br>0.93<br>0.86<br>0.5<br>0.90<br>0.87<br>0.6<br>0.89<br>0.78<br>0.1<br>0.81|

**Continuous and Textual Annotation Tasks**

|Col1|SummEval (ε = 0.2)|10K Prompts (ε = 0.15)|CEBaB-S (ε = 0.1)|Lesion (ε = 0.15)|KiloGram (ε = 0.1)|
|---|---|---|---|---|---|
|Gemini-Flash<br>Gemini-Pro<br>GPT-4o<br>GPT-4o-mini<br>Llama-3.1<br>Mistral-v3|Pears<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.51<br>0.0<br>0.46<br>0.47<br>0.0<br>0.44<br>0.54<br>0.0<br>0.48<br>0.50<br>0.0<br>0.54<br>0.36<br>0.0<br>0.58<br>0.12<br>0.0<br>**0.62**|Pears<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.44<br>0.31<br>0.67<br>0.33<br>0.08<br>0.63<br>0.47<br>0.69<br>0.76<br>0.46<br>0.92<br>**0.80**<br>0.23<br>0.15<br>0.67<br>0.28<br>0.15<br>0.67|Pears<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.75<br>0.6<br>0.82<br>0.78<br>0.8<br>0.87<br>0.80<br>0.9<br>**0.90**<br>0.79<br>0.9<br>0.89<br>0.78<br>0.6<br>0.85<br>0.76<br>0.5<br>0.83|Pears<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.70<br>0.17<br>0.71<br>0.73<br>1.0<br>**0.81**<br>0.67<br>0.0<br>0.62<br>0.72<br>0.67<br>0.73<br>–<br>–<br>–<br>–<br>–<br>–|Sim<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.79<br>0.66<br>**0.61**<br>0.77<br>0.08<br>0.43<br>0.78<br>0.2<br>0.53<br>0.78<br>0.16<br>0.49<br>–<br>–<br>–<br>–<br>–<br>–|

Table 2: **Main Results (zero-shot) — Full Datasets:** For all tasks, we report a traditional LLM-human alignment
measure, such as accuracy with the majority vote (Acc) for discrete tasks, Pearson’s correlation (Pears) for continuous
tasks, and average similarity (Sim) for textual tasks. Additionally, we present our proposed measures: the winning
rate (WR _ω_, the _ε_ value is stated next to the dataset name) and the average advantage probability (AP _ρ_ ). Bold
values indicate the best-performing LLM according to _ρ_, while a light green background highlights _ω_ _≥_ 0 _._ 5.

where applicable, adhere to the annotation guidelines outlined in the papers describing the dataset.
In addition to the basic _Zero-shot_ strategy, we
experimented with three advanced LLM-as-a-judge
strategies (Li et al., 2024a): _Few-shot_ (also known
as In-Context Learning), where the prompt includes four randomly sampled demonstrations (an
input paired with its majority vote label); _Chain-_
_of-Thought (CoT)_, where the prompt instructs the
LLM to reason step-by-step and provide an explanation before making a prediction; and _Ensemble_,
where the final prediction is determined by the majority label across an ensemble of LLMs and different prompting strategies (Nahum et al., 2024).

**5** **Results**

Table 2 presents the performance of various LLMs
across discrete, continuous, and free-text tasks. We
report three key measures: traditional LLM-human
alignment measures (accuracy, Pearson’s correlation, and similarity), the winning rate (WR, denoted
as _ω_ ), and the average advantage probability (AP,
denoted as _ρ_ ). For each dataset, we selected _ε_ values based on the type of annotators (as indicated
in Table 1): experts ( _ε_ = 0 _._ 2), skilled annotators
( _ε_ = 0 _._ 15), and crowd-workers ( _ε_ = 0 _._ 1). See
the discussion in §B.1 for an explanation of these
choices. Below, we summarize our main findings:

**LLMs can sometimes replace humans.** Table 2
shows that many LLMs pass the alt-test across various datasets. While in two datasets (MT-Bench,

and SummEval), none of the LLMs pass the test, in
four (Framing, CEBAB-A, CEBaB-S and Lesion),
almost all LLMs achieve _ω_ _≥_ 0 _._ 5. In the free-text
dataset KiloGram, only Gemini-Flash passes the
test. The results suggest that _in many scenarios, em-_
_ploying LLMs can be an alternative to recruiting_
_additional human annotators._

However, this positive news does not imply that
LLMs can always replace human annotators. The
success of LLMs is nuanced and aspect-dependent.
In Table 5 in the Appendix, we analyze three
datasets, breaking them down into sub-annotation
tasks corresponding to different aspects. For instance, in the SummEval dataset (which will be
discussed later), summary annotations are divided
into four aspects: coherence, consistency, fluency,
and relevance. Notably, each aspect may require
varying levels of expertise and capabilities, and indeed, the performance of LLMs varies accordingly.

In the Lesion dataset, which involves annotating
five aspects of skin lesion images, all LLMs pass
our test on color-related aspects (e.g., identifying
the number of colors or the presence of a bluish
glow) but struggle with shape-related aspects, such
as assessing asymmetry or border irregularity. In
the LGBTeen dataset, all LLMs excel in the sensitivity aspect, while for five other aspects (out of
ten), only one or two LLMs pass the test. In the
remaining four aspects, all LLMs fail. Notably, the
aspects where LLMs struggle often require higher
emotional intelligence or contextual understanding

16057

**3 Annotators and 100 Instances Subsets** (mean values computed over 100 bootstraps)

|Col1|WAX (ε = 0.1)|LGBTeen (ε = 0.2)|MT-Bench (ε = 0.2)|SummEval (ε = 0.2)|10K Prompts (ε = 0.15)|
|---|---|---|---|---|---|
|Gemini-Flash<br>+ 4-shots<br>+ CoT|Acc<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.37<br>0.08<br>0.66<br>0.41<br>0.19<br>0.70<br>0.38<br>0.09<br>0.69|Acc<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.55<br>0.02<br>0.74<br>0.66<br>0.61<br>**0.83**<br>0.47<br>0.0<br>0.70|Acc<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.63<br>0.0<br>0.72<br>0.61<br>0.0<br>0.73<br>0.63<br>0.01<br>0.76|Pears<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.47<br>0.0<br>0.48<br>0.60<br>0.41<br>0.76<br>0.47<br>0.0<br>0.46|Pears<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.36<br>0.09<br>0.66<br>0.40<br>0.58<br>0.76<br>0.37<br>0.01<br>0.61|
|Gemini-Pro<br>+ 4-shots<br>+ CoT|0.40<br>0.15<br>0.70<br>0.39<br>0.17<br>0.69<br>0.36<br>0.09<br>0.68|0.50<br>0.0<br>0.69<br>0.55<br>0.04<br>0.73<br>0.48<br>0.0<br>0.70|0.62<br>0.01<br>0.76<br>0.63<br>0.03<br>0.77<br>0.58<br>0.0<br>0.76|0.42<br>0.0<br>0.43<br>0.57<br>0.59<br>0.77<br>0.49<br>0.0<br>0.56|0.28<br>0.01<br>0.61<br>0.24<br>0.0<br>0.60<br>0.32<br>0.01<br>0.64|
|GPT-4o<br>+ 4-shots<br>+ CoT|0.37<br>0.17<br>0.69<br>0.39<br>0.15<br>0.69<br>0.37<br>0.11<br>0.70|0.65<br>0.55<br>0.82<br>0.55<br>0.03<br>0.75<br>0.65<br>0.43<br>0.81|0.69<br>0.16<br>0.78<br>0.66<br>0.13<br>0.78<br>0.65<br>0.4<br>**0.79**|0.52<br>0.0<br>0.49<br>0.58<br>0.28<br>0.74<br>0.58<br>0.03<br>0.67|0.41<br>0.27<br>0.73<br>0.38<br>0.16<br>0.72<br>0.37<br>0.43<br>0.74|
|GPT-4o-mini<br>+ 4-shots<br>+ CoT|0.27<br>0.0<br>0.59<br>0.30<br>0.01<br>0.62<br>0.33<br>0.0<br>0.66|0.59<br>0.1<br>0.78<br>0.60<br>0.12<br>0.77<br>0.57<br>0.06<br>0.75|0.60<br>0.0<br>0.73<br>0.61<br>0.0<br>0.74<br>0.59<br>0.0<br>0.72|0.49<br>0.0<br>0.53<br>0.60<br>0.77<br>**0.79**<br>0.56<br>0.0<br>0.60|0.36<br>0.48<br>0.76<br>0.42<br>0.74<br>**0.78**<br>0.32<br>0.44<br>0.74|
|Ens. Geminis<br>Ens. GPTs<br>Ens. All|0.42<br>0.21<br>0.71<br>0.38<br>0.05<br>0.67<br>0.44<br>0.24<br>**0.73**|0.56<br>0.11<br>0.77<br>0.61<br>0.19<br>0.79<br>0.63<br>0.37<br>0.80|0.66<br>0.03<br>0.76<br>0.60<br>0.0<br>0.73<br>0.61<br>0.01<br>0.74|0.48<br>0.0<br>0.55<br>0.58<br>0.04<br>0.66<br>0.58<br>0.02<br>0.66|0.33<br>0.06<br>0.67<br>0.39<br>0.64<br>0.77<br>0.39<br>0.41<br>0.74|

Table 3: **Results – Advanced LLM Judges:** Each data point is calculated using a bootstrap of 100 combinations of
three annotators and one hundred instances. _Ens._ stands for “Ensemble”. Please see the caption of Table 2.

(e.g., the Mental and Completeness aspects; see
Lissak et al. (2024)). Finally, in SummEval, most
LLMs pass the test for two aspects, Coherence and
Relevance, but fail on the other two.
Our results demonstrate that test success depends
on the dataset and annotation aspect, with LLMs
often failing to pass it. This emphasizes the relevance of the alt-test: researchers cannot simply rely
on LLM annotations without justifying this choice.

**Traditional measures strongly correlate with the**
**average advantage probability.** In addition to
the statistical procedure, our method enables comparing LLM judges using the average advantage
probability, _ρ_ . In subsection §3.4, we outlined the
desired properties of _ρ_, such as its interpretability
(as it directly represents the likelihood of the LLM
being as good as or better than a random annotator) and its flexibility, allowing it to be applied to
various types of annotation tasks.
Notably, in almost all datasets, the top-ranked
LLM is the same based on _ρ_ values and the traditional measures. Furthermore, in discrete tasks, the
ranking of models based on Accuracy and _ρ_ shows
a strong correlation, with an average Kendall _τ_
value of 0.92. Other tasks also correlate highly,
with an average Kendall _τ_ value of 0.84, except
for SummEval, which shows a negative correlation.
We discuss this anomaly in Appendix B.3, which
can be partially attributed to label imbalance (see
Appendix C.1 for a solution to handling imbalance)

**Few-Shot** **improves** **LLM-human** **alignment.**
Table 2 indicates that the closed-source LLMs
(GPTs and Geminis), outperform open-source

LLMs. [10] In discrete tasks, GPT-4o and Gemini-Pro
consistently are the best-performing LLMs, while
in continuous tasks, no single model emerges as
the clear winner. However, Table 2 reports only
zero-shot experiments. Thus, we also conducted
experiments using three other strategies: few-shot,
CoT, and ensemble. The results are presented in
Table 3 and are based on 100 bootstraps of three annotators and 100 randomly sampled instances from
five datasets. The reduced sample size was chosen
to minimize computational costs [11] and primarily
to reflect practical constraints better, as researchers
are unlikely to annotate thousands of instances for
testing whether the LLM is a good judge.
As shown in Table 3, the few-shot approach
(with four demonstrations) improved the performance of nearly all LLM judges. Importantly, two
few-shot LLMs achieved _ω_ _≥_ 0 _._ 5 on SummEval,
a result not observed in the zero-shot setting. This
success can be attributed to the demonstrations in
the prompt, which helped align the LLMs’ scoring
distributions more closely with the human distributions. In contrast, the CoT methodology led to a
decline in performance in many cases (45%). Finally, the ensemble method did not improve the
few-shot approach without ensembling.

**5.1** **The Number Of Instances**

To help researchers reduce the costly need for manual annotations, we propose a statistical procedure

10Further experiments across varying model sizes are necessary to support broader claims about model openness.
11We annotated a maximum of 300 instances per dataset,
which were then used for bootstrapping.

16058

LGBTeen - GPT-4o

50 100 150 200

10K Prompts - GPT-4o-mini

50 100 150 200

MT-Bench - GPT-4o

50 100 150 200

CEBaB-S - GPT-4o

50 100 150 200

Framing - GPT-4o

50 100 150 200

Lesion - Gemini-Pro

50 100 150 200

CEBaB-A - Gemini-Pro

50 100 150 200

KiloGram - Gemini-Flash

50 100 150 200

WAX - Gemini-Pro

50 100 150 200

SummEval - Mistral-v3

50 100 150 200

Figure 2: **Analysis of the Impact of the Number of Items:** Each data point is calculated using a bootstrap of
100 combinations of three annotators and _n_ items (x-axis). The y-axis shows the winning rates ( _ω_, solid lines) for
_ε_ = 0 _._ 1 (purple) and _ε_ = 0 _._ 2 (turquoise). In addition, it presents the average advantage probability ( _ρ_, dashed
brown line) with its empirical 0.9 confidence intervals. The subplot title indicates the examined LLM.

that requires only a subset of such annotations and
can verify whether an LLM can be used instead.
This naturally leads to the question: how many
annotated instances are needed for a reliable test?
To answer this, we present a bootstrap analysis in
Figure 2 illustrating how the number of instances
impacts our measures for the best-performing LLM
(according to _ρ_ ) in each dataset.
As shown, the winning rate _ω_ strongly depends
on the number of instances. This is because _ω_ reflects the number of rejected hypotheses (i.e., the
number of annotators the LLM wins), and more
instances increase the power of the statistical test
and the likelihood of rejecting a false null hypothesis (the human wins). In contrast, since _ρ_ does not
involve hypothesis testing, it is not affected _on ex-_
_pectation_ by the number of instances. Yet, increasing the number of instances reduces the variance of
_ρ_ (since it is a mean of means), making it a more
robust measure for comparing LLM judges.
Regarding the recommended number, beyond
the minimum requirement of 30 instances to satisfy
the normality assumption of the _t_ -test, Figure 2
shows that for _ε_ = 0 _._ 2, in most cases, the LLM begins to pass the test before annotating 100 instances,
and in half even before 50 instances. With _ε_ = 0 _._ 1
the alt-test requires more instances, typically double the amount needed for _ε_ = 0 _._ 2, between 100
and 150. Yet, in three datasets (LGBTeen, MTBench, and SummEval), the LLM fails to pass the
test regardless of the number of instances. While
the exact number may vary depending on the task,
the number of annotators, and the _ε_ value, our analysis highlights a promising finding: _only a modest_

_subset of annotations is required._

**6** **Conclusion**

Science advances through systematic observation,
precise measurement, and the rigorous validation
of hypotheses. It is no coincidence that Pearson
famously claimed statistics to be _“the grammar of_
_science”_ . As results and findings of studies increasingly rely on LLMs instead of human annotators,
extra care is needed to uphold scientific rigor.
In this paper, we proposed a statistical procedure to justify using LLM annotations in research
studies, the alt-test, which is simple and requires
minimal effort. As demonstrated in our analysis,
researchers can recruit a small group of annotators
(at least three) to annotate a subset of 50 to 100
examples, depending on the complexity of the task.
Appendix A provides a list of frequently asked
questions about our procedure, along with answers
and best practices. Then, in Appendix B, we further discuss and analyze additional aspects of our
procedure, like the impact of _ε_ and the choice of
human annotators. Finally, in Appendix C, we
propose modifications to our procedure to address
advanced scenarios: handling imbalanced labels
(§C.1), benchmarking against a single expert annotator (§C.2), incorporating annotator quality scores
(§C.3), respecting minotiy opinions in subjective
annotation tasks (§C.4), and testing whether LLMs
outperform humans (§C.5).
We encourage researchers to adopt our procedure to ensure more reliable and transparent evaluations of LLMs, and careful practices to leverage
their annotations in NLP research and other fields.

16059

**7** **Limitations**

**Data** **contamination** One limitation of our experiments is the potential for data contamination,
where datasets used in our experiments may overlap with the training data of the evaluated LLMs.
Popular datasets such as SummEval and MT-Bench,
commonly used for benchmarking LLM-as-judges,
are publicly available and might have been included
in the training data of some LLMs. Notice that
most of the datasets we used are recent (published
after 2022) and not widely known, with fewer than
50 citations each. Additionally, one of our datasets,
LGBTeen, is available only upon request. Hopefully, this lowers the risk of data contamination.

**High** **disagreement** **among** **human** **annotators**
High disagreement among human annotators can
arise from various factors, such as untrained crowd
workers, annotators who are not suited for the task,
unclear or poorly designed annotation guidelines,
or the inherently subjective nature of the task itself. In such cases, it is unlikely that the LLMas-a-judge will succeed in passing our test. The
procedure compares the LLM with each annotator
to test alignment with the remaining annotators.
When the remaining annotators are inconsistent,
this introduces high variance in determining who
aligns better (the LLM or the excluded annotator).
Under these conditions, the hypothesis test is unlikely to reject the null hypothesis, and the LLM’s
winning rate remains low.
This property of our procedure can be desirable,
as it may help researchers identify potential issues
with the annotation process, such as unclear guidelines, unqualified annotators, or the inherent subjectivity of the task. Traditional measures would
similarly yield low scores in such cases.
For inherently subjective tasks, we advocate for
developing alternative methods to assess the quality
of human annotations, where disagreements are a
feature rather than a flaw (Basile et al., 2021; Uma
et al., 2021) and methods to evaluate the LLM-as-ajudge’s ability to represent a spectrum of opinions.
Finally, we refer readers to §C.4 in the Appendix,
where we discuss modifications of our procedure
to better account for subjectivity and emphasize
minority opinions.

**Comparing against weak human annotators** A
potential misuse of our procedure is intentionally
comparing the LLM against weak human annotators to demonstrate that the LLM outperforms them

and justify its use. In cases where human annotators are noisy or random, with low inter-annotator
agreement, our procedure is unlikely to let the LLM
pass the test, as explained in the previous discussion on high disagreements.
However, there is a scenario where statistical
rigor cannot compensate for intentionally weak human annotators. In the single expert scenario (see
Appendix C.2), the LLM is compared against nonexperts, and both are tested for alignment with a
single expert. If the non-experts are particularly
weak (e.g., inconsistent or unqualified), the LLM
may appear to outperform them, and our procedure
cannot fully prevent such misuse.
Science, however, is built on transparency and
trust. We strongly encourage researchers to disclose detailed information about the annotators and
to publish the human annotations, allowing others
to reproduce and validate the results. As discussed
in §B, the expertise of the human annotators directly impacts the reliability and authority of the
procedure. Readers and reviewers should critically
assess the choice of annotators, and if the annotators are deemed unsuitable, the study’s results
should be taken with a grain of salt.

**References**

Eldar D Abraham, Karel D’Oosterlinck, Amir Feder,
Yair Gat, Atticus Geiger, Christopher Potts, Roi Reichart, and Zhengxuan Wu. 2022. Cebab: Estimating
the causal effects of real-world concepts on nlp model
behavior. _Advances in Neural Information Process-_
_ing Systems_, 35:17582–17596.

Josh Achiam, Steven Adler, Sandhini Agarwal, Lama
Ahmad, Ilge Akkaya, Florencia Leoni Aleman,
Diogo Almeida, Janko Altenschmidt, Sam Altman,
Shyamal Anadkat, et al. 2023. Gpt-4 technical report.
_arXiv preprint arXiv:2303.08774_ .

Gati V. Aher, Rosa I. Arriaga, and Adam Tauman Kalai.
2023\. [Using large language models to simulate mul-](https://proceedings.mlr.press/v202/aher23a.html)
tiple humans and [replicate](https://proceedings.mlr.press/v202/aher23a.html) human subject studies.
In _International_ _Conference_ _on_ _Machine_ _Learning,_
_ICML_ _2023,_ _23-29_ _July_ _2023,_ _Honolulu,_ _Hawaii,_
_USA_, volume 202 of _Proceedings of Machine Learn-_
_ing Research_, pages 337–371. PMLR.

Toufique Ahmed, Premkumar T. Devanbu, Christoph
Treude, and Michael Pradel. 2024. [Can llms replace](https://doi.org/10.48550/ARXIV.2408.05534)
[manual annotation of software engineering artifacts?](https://doi.org/10.48550/ARXIV.2408.05534)
_CoRR_, abs/2408.05534.

Anastasios N. Angelopoulos, Stephen Bates, Clara
Fannjiang, Michael I. Jordan, and Tijana Zrnic.
2023a. [Prediction-powered](https://doi.org/10.48550/ARXIV.2301.09633) inference. _CoRR_,
abs/2301.09633.

16060

Anastasios N. Angelopoulos, John C. Duchi, and Tijana
Zrnic. 2023b. PPI++: [efficient prediction-powered](https://doi.org/10.48550/ARXIV.2311.01453)
[inference.](https://doi.org/10.48550/ARXIV.2311.01453) _CoRR_, abs/2311.01453.

Zahra Ashktorab, Michael Desmond, Qian Pan,
James M. Johnson, Martin Santillan Cooper, Elizabeth M. Daly, Rahul Nair, Tejaswini Pedapati, Swapnaja Achintalwar, and Werner Geyer. 2024. [Aligning](https://doi.org/10.48550/ARXIV.2410.00873)
[human and LLM judgments:](https://doi.org/10.48550/ARXIV.2410.00873) Insights from evalassist
on task-specific [evaluations](https://doi.org/10.48550/ARXIV.2410.00873) and ai-assisted assess[ment strategy preferences.](https://doi.org/10.48550/ARXIV.2410.00873) _CoRR_, abs/2410.00873.

Yushi Bai, Jiahao Ying, Yixin Cao, Xin Lv, Yuze
He, Xiaozhi Wang, Jifan Yu, Kaisheng Zeng, Yijia Xiao, Haozhe Lyu, Jiayin Zhang, Juanzi Li, and
Lei Hou. 2023. Benchmarking [foundation](http://papers.nips.cc/paper_files/paper/2023/hash/f64e55d03e2fe61aa4114e49cb654acb-Abstract-Datasets_and_Benchmarks.html) models
[with language-model-as-an-examiner.](http://papers.nips.cc/paper_files/paper/2023/hash/f64e55d03e2fe61aa4114e49cb654acb-Abstract-Datasets_and_Benchmarks.html) In _Advances_
_in_ _Neural_ _Information_ _Processing_ _Systems_ _36:_ _An-_
_nual Conference on Neural Information Processing_
_Systems 2023, NeurIPS 2023, New Orleans, LA, USA,_
_December 10 - 16, 2023_ .

Henning Bartsch, Ole Jorgensen, Domenic Rosati, Jason
Hoelscher-Obermaier, and Jacob Pfau. 2023. Selfconsistency of large language models under ambiguity. _arXiv preprint arXiv:2310.13439_ .

Valerio Basile, Michael Fell, Tommaso Fornaciari, Dirk
Hovy, Silviu Paun, Barbara Plank, Massimo Poesio,
Alexandra Uma, et al. 2021. We need to consider
disagreement in evaluation. In _Proceedings_ _of_ _the_
_1st_ _workshop_ _on_ _benchmarking:_ _past,_ _present_ _and_
_future_, pages 15–21. Association for Computational
Linguistics.

Anna Bavaresco, Raffaella Bernardi, Leonardo Bertolazzi, Desmond Elliott, Raquel Fernández, Albert
Gatt, Esam Ghaleb, Mario Giulianelli, Michael
Hanna, Alexander Koller, André F. T. Martins,
Philipp Mondorf, Vera Neplenbroek, Sandro Pezzelle,
Barbara Plank, David Schlangen, Alessandro Suglia, Aditya K. Surikuchi, Ece Takmaz, and Alberto
Testoni. 2024. Llms instead of [human](https://doi.org/10.48550/ARXIV.2406.18403) judges? A
[large scale empirical study across 20 NLP evaluation](https://doi.org/10.48550/ARXIV.2406.18403)
[tasks.](https://doi.org/10.48550/ARXIV.2406.18403) _CoRR_, abs/2406.18403.

Yoav Benjamini and Daniel Yekutieli. 2001. The control of the false discovery rate in multiple testing
under dependency. _Annals of statistics_, pages 1165–
1188\.

Nitay Calderon and Roi Reichart. 2024. On behalf of
the stakeholders: Trends in nlp model interpretability
in the era of llms. _arXiv preprint arXiv:2407.19200_ .

Ivi Chatzi, Eleni Straitouri, Suhas Thejaswi, and
Manuel Gomez Rodriguez. 2024. [Prediction-](https://doi.org/10.48550/ARXIV.2402.17826)
[powered ranking of large language models.](https://doi.org/10.48550/ARXIV.2402.17826) _CoRR_,
abs/2402.17826.

Beiduo Chen, Xinpeng Wang, Siyao Peng, Robert
Litschko, Anna Korhonen, and Barbara Plank. 2024a.
["seeing the big through the small":](https://aclanthology.org/2024.findings-emnlp.842) Can llms approx[imate human judgment distributions on NLI from a](https://aclanthology.org/2024.findings-emnlp.842)
[few explanations?](https://aclanthology.org/2024.findings-emnlp.842) In _Findings of the Association for_
_Computational_ _Linguistics:_ _EMNLP_ _2024,_ _Miami,_

_Florida, USA, November 12-16, 2024_, pages 14396–
14419\. Association for Computational Linguistics.

Dongping Chen, Ruoxi Chen, Shilin Zhang, Yinuo
Liu, Yaochen Wang, Huichi Zhou, Qihui Zhang, Pan
Zhou, Yao Wan, and Lichao Sun. 2024b. Mllmas-a-judge: Assessing multimodal llm-as-a-judge
with vision-language benchmark. _arXiv_ _preprint_
_arXiv:2402.04788_ .

Guiming Hardy Chen, Shunian Chen, Ziche Liu, Feng
Jiang, and Benyou Wang. 2024c. Humans or llms
as the judge? a study on judgement biases. _arXiv_
_preprint arXiv:2402.10669_ .

Veronika Cheplygina and Josien P. W. Pluim. 2018.

[Crowd disagreement about medical images is infor-](https://doi.org/10.1007/978-3-030-01364-6_12)
[mative.](https://doi.org/10.1007/978-3-030-01364-6_12) In _Intravascular_ _Imaging_ _and_ _Computer_
_Assisted_ _Stenting_ _and_ _Large-Scale_ _Annotation_ _of_
_Biomedical_ _Data_ _and_ _Expert_ _Label_ _Synthesis._ _LA-_
_BELS, CVII, STENT 2018_, volume 11043 of _Lecture_
_Notes in Computer Science_, pages 62–70. Springer,
Cham.

Cheng-Han Chiang and Hung-yi Lee. 2023. [Can large](https://doi.org/10.18653/v1/2023.acl-long.870)
[language models be an alternative to human evalua-](https://doi.org/10.18653/v1/2023.acl-long.870)
[tions?](https://doi.org/10.18653/v1/2023.acl-long.870) In _Proceedings of the 61st Annual Meeting of_
_the Association for Computational Linguistics (Vol-_
_ume 1:_ _Long Papers)_, pages 15607–15631, Toronto,
Canada. Association for Computational Linguistics.

Wei-Lin Chiang, Zhuohan Li, Zi Lin, Ying Sheng,
Zhanghao Wu, Hao Zhang, Lianmin Zheng, Siyuan
Zhuang, Yonghao Zhuang, Joseph E Gonzalez, et al.
2023\. Vicuna: An open-source chatbot impressing
gpt-4 with 90%\* chatgpt quality. _See https://vicuna._
_lmsys. org (accessed 14 April 2023)_, 2(3):6.

Noel C. F. Codella, David A. Gutman, M. Emre Celebi,
Brian Helba, Michael A. Marchetti, Stephen W.
Dusza, Aadi Kalloo, Konstantinos Liopyris, Nabin K.
Mishra, Harald Kittler, and Allan Halpern. 2018.
[Skin lesion analysis toward melanoma detection:](https://doi.org/10.1109/ISBI.2018.8363547) A
challenge at the 2017 [international](https://doi.org/10.1109/ISBI.2018.8363547) symposium on
[biomedical imaging (isbi), hosted by the international](https://doi.org/10.1109/ISBI.2018.8363547)
[skin imaging collaboration (ISIC).](https://doi.org/10.1109/ISBI.2018.8363547) In _15th IEEE In-_
_ternational Symposium on Biomedical Imaging, ISBI_
_2018, Washington, DC, USA, April 4-7, 2018_, pages
168–172. IEEE.

Yijiang River Dong, Tiancheng Hu, and Nigel Collier.
2024\. Can llm be a personalized judge? _arXiv_
_preprint arXiv:2406.11657_ .

Rotem Dror, Gili Baumer, Marina Bogomolov, and Roi
Reichart. 2017. Replicability analysis for natural
language processing: Testing significance with multiple datasets. _Transactions_ _of_ _the_ _Association_ _for_
_Computational Linguistics_, 5:471–486.

Rotem Dror, Gili Baumer, Segev Shlomov, and Roi
Reichart. 2018. The hitchhiker’s guide to testing
statistical significance in natural language processing.
In _Proceedings_ _of_ _the_ _56th_ _annual_ _meeting_ _of_ _the_
_association for computational linguistics (volume 1:_
_Long papers)_, pages 1383–1392.

16061

Naoki Egami, Musashi Hinck, Brandon M. Stewart,
and Hanying Wei. 2023. [Using imperfect surrogates](http://papers.nips.cc/paper_files/paper/2023/hash/d862f7f5445255090de13b825b880d59-Abstract-Conference.html)
[for downstream inference:](http://papers.nips.cc/paper_files/paper/2023/hash/d862f7f5445255090de13b825b880d59-Abstract-Conference.html) Design-based supervised
[learning for social science applications of large lan-](http://papers.nips.cc/paper_files/paper/2023/hash/d862f7f5445255090de13b825b880d59-Abstract-Conference.html)
[guage models.](http://papers.nips.cc/paper_files/paper/2023/hash/d862f7f5445255090de13b825b880d59-Abstract-Conference.html) In _Advances in Neural Information_
_Processing Systems 36:_ _Annual Conference on Neu-_
_ral Information Processing Systems 2023, NeurIPS_
_2023,_ _New_ _Orleans,_ _LA,_ _USA,_ _December_ _10_ _-_ _16,_
_2023_ .

Alexander R Fabbri, Wojciech Kry´sci´nski, Bryan McCann, Caiming Xiong, Richard Socher, and Dragomir
Radev. 2021. Summeval: Re-evaluating summarization evaluation. _Transactions of the Association for_
_Computational Linguistics_, 9:391–409.

Lea Frermann, Jiatong Li, Shima Khanehzar, and Gosia
Mikolajczak. 2023. [Conflicts, villains, resolutions:](https://doi.org/10.18653/v1/2023.acl-long.486)
[Towards models of narrative media framing.](https://doi.org/10.18653/v1/2023.acl-long.486) In _Pro-_
_ceedings of the 61st Annual Meeting of the Associa-_
_tion for Computational Linguistics (Volume 1:_ _Long_
_Papers)_, pages 8712–8732, Toronto, Canada. Association for Computational Linguistics.

Yair Ori Gat, Nitay Calderon, Amir Feder, Alexander
Chapanin, Amit Sharma, and Roi Reichart. 2024.
[Faithful explanations of black-box NLP models us-](https://openreview.net/forum?id=UMfcdRIotC)
ing [llm-generated](https://openreview.net/forum?id=UMfcdRIotC) counterfactuals. In _The_ _Twelfth_
_International_ _Conference_ _on_ _Learning_ _Representa-_
_tions, ICLR 2024, Vienna, Austria, May 7-11, 2024_ .
OpenReview.net.

Zorik Gekhman, Jonathan Herzig, Roee Aharoni, Chen
Elkind, and Idan Szpektor. 2023. [Trueteacher: Learn-](https://doi.org/10.18653/V1/2023.EMNLP-MAIN.127)
ing factual consistency [evaluation](https://doi.org/10.18653/V1/2023.EMNLP-MAIN.127) with large lan[guage models.](https://doi.org/10.18653/V1/2023.EMNLP-MAIN.127) In _Proceedings of the 2023 Confer-_
_ence on Empirical Methods in Natural Language Pro-_
_cessing, EMNLP 2023, Singapore, December 6-10,_
_2023_, pages 2053–2070. Association for Computational Linguistics.

Ariel Gera, Odellia Boni, Yotam Perlitz, Roy Bar-Haim,
Lilach Eden, and Asaf Yehudai. 2024. Justrank:
Benchmarking llm judges for system ranking. _arXiv_
_preprint arXiv:2412.09569_ .

Fabrizio Gilardi, Meysam Alizadeh, and Maël Kubli.
2023\. [Chatgpt outperforms crowd-workers for text-](https://doi.org/10.48550/ARXIV.2303.15056)
[annotation tasks.](https://doi.org/10.48550/ARXIV.2303.15056) _CoRR_, abs/2303.15056.

Kristina Gligoric, Tijana Zrnic, Cinoo Lee, Emmanuel J.
Candès, and Dan Jurafsky. 2024. [Can unconfident](https://doi.org/10.48550/ARXIV.2408.15204)
[LLM annotations be used for confident conclusions?](https://doi.org/10.48550/ARXIV.2408.15204)
_CoRR_, abs/2408.15204.

Jiawei Gu, Xuhui Jiang, Zhichao Shi, Hexiang Tan,
Xuehao Zhai, Chengjin Xu, Wei Li, Yinghan Shen,
Shengjie Ma, Honghao Liu, et al. 2024. A survey on
llm-as-a-judge. _arXiv preprint arXiv:2411.15594_ .

Adam Hadhazy. 2023. [Chatgpt out-scores medical stu-](https://hai.stanford.edu/news/chatgpt-out-scores-medical-students-complex-clinical-care-exam-questions)
[dents on complex clinical care exam questions.](https://hai.stanford.edu/news/chatgpt-out-scores-medical-students-complex-clinical-care-exam-questions) Accessed: 2025-01-07.

Oana Inel, Khalid Khamkham, Tatiana Cristea, Anca
Dumitrache, Arne Rutjes, Jelle van der Ploeg, Lukasz

Romaszko, Lora Aroyo, and Robert-Jan Sips. 2014.
Crowdtruth: [Machine-human](https://doi.org/10.1007/978-3-319-11915-1_31) computation framework for harnessing [disagreement](https://doi.org/10.1007/978-3-319-11915-1_31) in gathering an[notated](https://doi.org/10.1007/978-3-319-11915-1_31) data. In _The_ _Semantic_ _Web_ _-_ _ISWC_ _2014_ _-_
_13th International Semantic Web Conference, Riva_
_del Garda, Italy, October 19-23, 2014. Proceedings,_
_Part II_, volume 8797 of _Lecture Notes in Computer_
_Science_, pages 486–504. Springer.

Anya Ji, Noriyuki Kojima, Noah Rush, Alane Suhr,
Wai Keen Vong, Robert Hawkins, and Yoav Artzi.
2022\. [Abstract visual reasoning with tangram shapes.](https://doi.org/10.18653/v1/2022.emnlp-main.38)
In _Proceedings of the 2022 Conference on Empirical_
_Methods in Natural Language Processing_, pages 582–
601, Abu Dhabi, United Arab Emirates. Association
for Computational Linguistics.

Dongfu Jiang, Yishan Li, Ge Zhang, Wenhao Huang,
Bill Yuchen Lin, and Wenhu Chen. 2024. [Tigerscore:](https://openreview.net/forum?id=EE1CBKC0SZ)
[Towards building explainable metric for all text gen-](https://openreview.net/forum?id=EE1CBKC0SZ)
[eration tasks.](https://openreview.net/forum?id=EE1CBKC0SZ) _Trans. Mach. Learn. Res._, 2024.

Lucas Joos, Daniel A. Keim, and Maximilian T. Fischer.
2024\. [Cutting through the clutter:](https://doi.org/10.48550/ARXIV.2407.10652) The potential of
llms for efficient [filtration](https://doi.org/10.48550/ARXIV.2407.10652) in systematic literature
[reviews.](https://doi.org/10.48550/ARXIV.2407.10652) _CoRR_, abs/2407.10652.

Jaehun Jung, Faeze Brahman, and Yejin Choi. 2024.
Trust or escalate: Llm judges with provable guarantees for human agreement. _arXiv_ _preprint_
_arXiv:2407.18370_ .

Qusai Khraisha, Sophie Put, Johanna Kappenberg, Azza
Warraitch, and Kristin Hadfield. 2024. Can large language models replace humans in systematic reviews?
evaluating gpt-4’s efficacy in screening and extracting data from peer-reviewed and grey literature in
multiple languages. _Research Synthesis Methods_ .

Seungone Kim, Jamin Shin, Yejin Choi, Joel Jang,
Shayne Longpre, Hwaran Lee, Sangdoo Yun,
Seongjin Shin, Sungdong Kim, James Thorne, and
Minjoon Seo. 2024. Prometheus: [Inducing](https://openreview.net/forum?id=8euJaTveKw) fine[grained evaluation capability in language models.](https://openreview.net/forum?id=8euJaTveKw) In
_The_ _Twelfth_ _International_ _Conference_ _on_ _Learning_
_Representations, ICLR 2024, Vienna, Austria, May_
_7-11, 2024_ . OpenReview.net.

Takeshi Kojima, Shixiang Shane Gu, Machel Reid, Yutaka Matsuo, and Yusuke Iwasawa. 2022. [Large lan-](http://papers.nips.cc/paper_files/paper/2022/hash/8bb0d291acd4acf06ef112099c16f326-Abstract-Conference.html)
[guage models are zero-shot reasoners.](http://papers.nips.cc/paper_files/paper/2022/hash/8bb0d291acd4acf06ef112099c16f326-Abstract-Conference.html) In _Advances_
_in_ _Neural_ _Information_ _Processing_ _Systems_ _35:_ _An-_
_nual Conference on Neural Information Processing_
_Systems 2022, NeurIPS 2022, New Orleans, LA, USA,_
_November 28 - December 9, 2022_ .

Nathan Lambert, Valentina Pyatkin, Jacob Morrison,
LJ Miranda, Bill Yuchen Lin, Khyathi Raghavi
Chandu, Nouha Dziri, Sachin Kumar, Tom Zick,
Yejin Choi, Noah A. Smith, and Hannaneh Hajishirzi.
2024\. Rewardbench: [Evaluating reward models for](https://doi.org/10.48550/ARXIV.2403.13787)
[language modeling.](https://doi.org/10.48550/ARXIV.2403.13787) _CoRR_, abs/2403.13787.

Md Tahmid Rahman Laskar, M Saiful Bari, Mizanur
Rahman, Md Amran Hossen Bhuiyan, Shafiq Joty,
and Jimmy Huang. 2023. A [systematic](https://doi.org/10.18653/v1/2023.findings-acl.29) study and

16062

[comprehensive evaluation of ChatGPT on benchmark](https://doi.org/10.18653/v1/2023.findings-acl.29)
[datasets.](https://doi.org/10.18653/v1/2023.findings-acl.29) In _Findings_ _of_ _the_ _Association_ _for_ _Com-_
_putational Linguistics:_ _ACL 2023_, pages 431–469,
Toronto, Canada. Association for Computational Linguistics.

Dawei Li, Bohan Jiang, Liangjie Huang, Alimohammad
Beigi, Chengshuai Zhao, Zhen Tan, Amrita Bhattacharjee, Yuxuan Jiang, Canyu Chen, Tianhao Wu,
et al. 2024a. From generation to judgment: Opportunities and challenges of llm-as-a-judge. _arXiv_
_preprint arXiv:2411.16594_ .

Haitao Li, Qian Dong, Junjie Chen, Huixue Su, Yujia Zhou, Qingyao Ai, Ziyi Ye, and Yiqun Liu.
2024b. Llms-as-judges: A comprehensive survey
on llm-based evaluation methods. _arXiv_ _preprint_
_arXiv:2412.05579_ .

Shir Lissak, Nitay Calderon, Geva Shenkman, Yaakov
Ophir, Eyal Fruchter, Anat Brunstein Klomek, and
Roi Reichart. 2024. The colorful [future](https://doi.org/10.18653/v1/2024.naacl-long.113) of LLMs:
[Evaluating and improving LLMs as emotional sup-](https://doi.org/10.18653/v1/2024.naacl-long.113)
[porters for queer youth.](https://doi.org/10.18653/v1/2024.naacl-long.113) In _Proceedings of the 2024_
_Conference_ _of_ _the_ _North_ _American_ _Chapter_ _of_ _the_
_Association for Computational Linguistics:_ _Human_
_Language_ _Technologies_ _(Volume_ _1:_ _Long_ _Papers)_,
pages 2040–2079, Mexico City, Mexico. Association
for Computational Linguistics.

Chunhua Liu, Trevor Cohn, Simon De Deyne, and Lea
Frermann. 2022. Wax: A new dataset for word association explanations. In _Proceedings_ _of_ _the_ _2nd_
_Conference of the Asia-Pacific Chapter of the Asso-_
_ciation for Computational Linguistics and the 12th_
_International Joint Conference on Natural Language_
_Processing (Volume 1:_ _Long Papers)_, pages 106–120.

Jens Ludwig, Sendhil Mullainathan, and Ashesh Rambachan. 2024. Large language models: An applied econometric framework. _arXiv_ _preprint_
_arXiv:2412.07031_ .

Xiaoliang Luo, Akilles Rechardt, Guangzhi Sun,
Kevin K Nejad, Felipe Yáñez, Bati Yilmaz, Kangjoo
Lee, Alexandra O Cohen, Valentina Borghesani, Anton Pashkov, et al. 2024. Large language models
surpass human experts in predicting neuroscience
results. _Nature Human Behaviour_, pages 1–11.

Behrad Moniri, Hamed Hassani, and Edgar Dobriban.
2024\. [Evaluating the performance of large language](https://doi.org/10.48550/ARXIV.2406.11044)
[models via debates.](https://doi.org/10.48550/ARXIV.2406.11044) _CoRR_, abs/2406.11044.

Omer Nahum, Nitay Calderon, Orgad Keller, Idan
Szpektor, and Roi Reichart. 2024. Are llms better
than reported? detecting label errors and mitigating
their effect on model performance. _arXiv_ _preprint_
_arXiv:2410.18889_ .

Aakanksha Naik, Bailey Kuehl, Erin Bransom, Doug
Downey, and Tom Hope. 2024. [CARE: extracting ex-](https://doi.org/10.18653/V1/2024.FINDINGS-NAACL.285)
[perimental findings from clinical literature.](https://doi.org/10.18653/V1/2024.FINDINGS-NAACL.285) In _Find-_
_ings of the Association for Computational Linguis-_
_tics:_ _NAACL 2024, Mexico City, Mexico, June 16-21,_
_2024_, pages 4580–4596. Association for Computational Linguistics.

Arbi Haza Nasution and Aytug Onan. 2024. [Chatgpt](https://doi.org/10.1109/ACCESS.2024.3402809)
[label: Comparing the quality of human-generated and](https://doi.org/10.1109/ACCESS.2024.3402809)
[llm-generated annotations in low-resource language](https://doi.org/10.1109/ACCESS.2024.3402809)
[NLP tasks.](https://doi.org/10.1109/ACCESS.2024.3402809) _IEEE Access_, 12:71876–71900.

Maja Pavlovic and Massimo Poesio. 2024. [The](https://doi.org/10.48550/ARXIV.2405.01299) effectiveness of llms as [annotators:](https://doi.org/10.48550/ARXIV.2405.01299) A comparative
[overview and empirical analysis of direct representa-](https://doi.org/10.48550/ARXIV.2405.01299)
[tion.](https://doi.org/10.48550/ARXIV.2405.01299) _CoRR_, abs/2405.01299.

Barbara Plank. 2022. [The “problem” of human label](https://doi.org/10.18653/v1/2022.emnlp-main.731)
variation: On ground [truth](https://doi.org/10.18653/v1/2022.emnlp-main.731) in data, modeling and
[evaluation.](https://doi.org/10.18653/v1/2022.emnlp-main.731) In _Proceedings of the 2022 Conference_
_on Empirical Methods in Natural Language Process-_
_ing_, pages 10671–10682, Abu Dhabi, United Arab
Emirates. Association for Computational Linguistics.

Itay Ravid and Rotem Dror. 2023. 140 characters of
justice? the promise and perils of using social media
to reveal lay punishment perspectives. _U. Ill. L. Rev._,
page 1473.

Marc Cicero Schubert, Wolfgang Wick, and Varun
Venkataramani. 2023. Performance of large language
models on a neurology board–style examination.
_JAMA network open_, 6(12):e2346721–e2346721.

Eilam Shapira, Omer Madmon, Roi Reichart, and
Moshe Tennenholtz. 2024. [Can large language mod-](https://doi.org/10.48550/ARXIV.2401.17435)
[els replace economic choice prediction labs?](https://doi.org/10.48550/ARXIV.2401.17435) _CoRR_,
abs/2401.17435.

Mingyang Song, Mao Zheng, and Xuan Luo. 2024.

[Can many-shot in-context learning help long-context](https://doi.org/10.48550/ARXIV.2406.11629)
LLM judges? see more, judge better! _CoRR_,
abs/2406.11629.

Annalisa Szymanski, Noah Ziems, Heather A. EicherMiller, Toby Jia-Jun Li, Meng Jiang, and Ronald A.
Metoyer. 2024. [Limitations of the llm-as-a-judge ap-](https://doi.org/10.48550/ARXIV.2410.20266)
[proach for evaluating LLM outputs in expert knowl-](https://doi.org/10.48550/ARXIV.2410.20266)
[edge tasks.](https://doi.org/10.48550/ARXIV.2410.20266) _CoRR_, abs/2410.20266.

Sijun Tan, Siyuan Zhuang, Kyle Montgomery,
William Y. Tang, Alejandro Cuadron, Chenguang
Wang, Raluca Ada Popa, and Ion Stoica. 2024a.
Judgebench: [A benchmark for evaluating llm-based](https://doi.org/10.48550/ARXIV.2410.12784)
[judges.](https://doi.org/10.48550/ARXIV.2410.12784) _CoRR_, abs/2410.12784.

Zhen Tan, Dawei Li, Song Wang, Alimohammad
Beigi, Bohan Jiang, Amrita Bhattacharjee, Mansooreh Karami, Jundong Li, Lu Cheng, and Huan
Liu. 2024b. [Large language models for data anno-](https://aclanthology.org/2024.emnlp-main.54)
tation and [synthesis:](https://aclanthology.org/2024.emnlp-main.54) A survey. In _Proceedings_ _of_
_the 2024 Conference on Empirical Methods in Natu-_
_ral Language Processing, EMNLP 2024, Miami, FL,_
_USA, November 12-16, 2024_, pages 930–957. Association for Computational Linguistics.

Sean Trott. 2024. [Large language models and the wis-](https://direct.mit.edu/opmi/article/doi/10.1162/opmi_a_00144/121179)
[dom of small crowds.](https://direct.mit.edu/opmi/article/doi/10.1162/opmi_a_00144/121179) _Open Mind_, 8:723–738.

Alexandra Uma, Tommaso Fornaciari, Dirk Hovy, Silviu Paun, Barbara Plank, and Massimo Poesio. 2021.
[Learning from disagreement:](https://doi.org/10.1613/JAIR.1.12752) A survey. _J. Artif. In-_
_tell. Res._, 72:1385–1470.

16063

Mor Ventura, Eyal Ben-David, Anna Korhonen, and Roi
Reichart. 2023. [Navigating cultural chasms:](https://doi.org/10.48550/ARXIV.2310.01929) Explor[ing and unlocking the cultural POV of text-to-image](https://doi.org/10.48550/ARXIV.2310.01929)
[models.](https://doi.org/10.48550/ARXIV.2310.01929) _CoRR_, abs/2310.01929.

Pat Verga, Sebastian Hofstatter, Sophia Althammer, Yixuan Su, Aleksandra Piktus, Arkady Arkhangorodsky,
Minjie Xu, Naomi White, and Patrick Lewis. 2024.
Replacing judges with juries: Evaluating llm generations with a panel of diverse models. _arXiv preprint_
_arXiv:2404.18796_ .

Peiyi Wang, Lei Li, Liang Chen, Zefan Cai, Dawei Zhu,
Binghuai Lin, Yunbo Cao, Lingpeng Kong, Qi Liu,
Tianyu Liu, and Zhifang Sui. 2024. [Large language](https://doi.org/10.18653/V1/2024.ACL-LONG.511)
[models are not fair evaluators.](https://doi.org/10.18653/V1/2024.ACL-LONG.511) In _Proceedings of the_
_62nd Annual Meeting of the Association for Compu-_
_tational Linguistics (Volume 1:_ _Long Papers), ACL_
_2024, Bangkok, Thailand, August 11-16, 2024_, pages
9440–9450. Association for Computational Linguistics.

Minghao Wu and Alham Fikri Aji. 2023. [Style over sub-](https://doi.org/10.48550/ARXIV.2307.03025)
stance: [Evaluation biases for large language models.](https://doi.org/10.48550/ARXIV.2307.03025)
_CoRR_, abs/2307.03025.

Wenda Xu, Guanglei Zhu, Xuandong Zhao, Liangming
Pan, Lei Li, and William Wang. 2024. [Pride and prej-](https://doi.org/10.18653/v1/2024.acl-long.826)
udice: LLM amplifies [self-bias](https://doi.org/10.18653/v1/2024.acl-long.826) in self-refinement.
In _Proceedings_ _of_ _the_ _62nd_ _Annual_ _Meeting_ _of_ _the_
_Association for Computational Linguistics (Volume 1:_
_Long Papers)_, pages 15474–15492, Bangkok, Thailand. Association for Computational Linguistics.

Jingfeng Yang, Hongye Jin, Ruixiang Tang, Xiaotian Han, Qizhang Feng, Haoming Jiang, Shaochen
Zhong, Bing Yin, and Xia Ben Hu. 2024. [Harness-](https://doi.org/10.1145/3649506)
[ing the power of llms in practice:](https://doi.org/10.1145/3649506) A survey on chat[gpt and beyond.](https://doi.org/10.1145/3649506) _ACM Trans. Knowl. Discov. Data_,
18(6):160:1–160:32.

Jiayi Ye, Yanbo Wang, Yue Huang, Dongping Chen,
Qihui Zhang, Nuno Moniz, Tian Gao, Werner Geyer,
Chao Huang, Pin-Yu Chen, Nitesh V. Chawla, and Xiangliang Zhang. 2024. [Justice or prejudice? quantify-](https://doi.org/10.48550/ARXIV.2410.02736)
[ing biases in llm-as-a-judge.](https://doi.org/10.48550/ARXIV.2410.02736) _CoRR_, abs/2410.02736.

Xiang Yue, Boshi Wang, Ziru Chen, Kai Zhang, Yu Su,
and Huan Sun. 2023. [Automatic evaluation of attri-](https://doi.org/10.18653/V1/2023.FINDINGS-EMNLP.307)
[bution by large language models.](https://doi.org/10.18653/V1/2023.FINDINGS-EMNLP.307) In _Findings of the_
_Association for Computational Linguistics:_ _EMNLP_
_2023, Singapore, December 6-10, 2023_, pages 4615–
4635\. Association for Computational Linguistics.

Lianmin Zheng, Wei-Lin Chiang, Ying Sheng, Siyuan
Zhuang, Zhanghao Wu, Yonghao Zhuang, Zi Lin,
Zhuohan Li, Dacheng Li, Eric Xing, et al. 2024a.
Judging llm-as-a-judge with mt-bench and chatbot
arena. _Advances in Neural Information Processing_
_Systems_, 36.

Lianmin Zheng, Wei-Lin Chiang, Ying Sheng, Siyuan
Zhuang, Zhanghao Wu, Yonghao Zhuang, Zi Lin,
Zhuohan Li, Dacheng Li, Eric P. Xing, Hao Zhang,
Joseph E. Gonzalez, and Ion Stoica. 2024b. Judging llm-as-a-judge with mt-bench and chatbot arena.

NIPS ’23, Red Hook, NY, USA. Curran Associates
Inc.

Lianghui Zhu, Xinggang Wang, and Xinlong Wang.
2023\. Judgelm: [Fine-tuned large language models](https://doi.org/10.48550/ARXIV.2310.17631)
[are scalable judges.](https://doi.org/10.48550/ARXIV.2310.17631) _CoRR_, abs/2310.17631.

Caleb Ziems, William Held, Omar Shaikh, Jiaao Chen,
Zhehao Zhang, and Diyi Yang. 2024. [Can large lan-](https://doi.org/10.1162/COLI_A_00502)
guage models transform computational social sci[ence?](https://doi.org/10.1162/COLI_A_00502) _Comput. Linguistics_, 50(1):237–291.

16064

## **Appendix**

**A** **Frequently Asked Questions** **15**

**B** **Discussion** **16**

B.1 The Cost-benefit Hyperparameter 17

B.2 The Human Annotators Profile 17

B.3 Case study: SummEval . . . . 18

**C** **Advanced Topics** **18**

C.1 Handling Imbalanced Labels . 18

C.2 A Single Expert Annotator . . . 19

C.3 Incorporating Annotator Quality 19

C.4 Subjective Annotation Tasks . . 20

C.5 Testing if LLMs Outperform Humans . . . . . . . . . . . . . . 20

C.6 The Benjamini-Yekutiali Procedure . . . . . . . . . . . . . . 20

**D** **The Optimal LLM-as-a-Judge** **21**

**E** **Datasets** **22**

**F** **Additional Results** **24**

**G** **Prompts** **25**

**A** **Frequently Asked Questions**

**Q: Why not use an Inter-Annotator Agreement**
**(IAA) measure?**
**A:** Our procedure is a type of IAA, but unlike traditional IAA measures (such as Cohen’s kappa),
which assess agreement among a group of annotators, our goal is to _compare_ the LLM to the group
to determine whether it can replace them.

**Q: Why not use a traditional measure such as**
**F1 score or accuracy?**
**A:** To compare the LLM to human annotators and
to address the ‘replacement question’ (i.e., whether
the LLM can be used instead of the annotators), one
might consider traditional LLM-human alignment
measures (e.g., the F1 score or a correlation between the LLM and the majority vote label). However, answering the replacement question requires
statistical rigor. Even though a statistical test can
check if the traditional measure exceeds a predefined threshold, there is no universal standard for

setting it, which may vary across datasets and setups. Additionally, traditional measures only evaluate whether the LLM matches human performance,
not whether it provides a better alternative.
In contrast, our procedure involves statistical
practices and provides clear passing criteria. Most
importantly, it directly answers the replacement
question by using a leave-one-out approach – excluding one annotator at a time and assessing
whether the LLM better represents the remaining
annotators than the excluded one.

**Q:** **Why** **do** **you** **recommend** **at** **least** **three** **hu-**
**man annotators and not two?**
**A:** While our procedure can be used with two annotators, we believe it is less reliable. With only
two, the procedure simply checks whether the LLM
aligns more with one annotator than the other, lacking a consensus signal. This makes results more
sensitive to individual biases. With at least three
annotators, the procedure better evaluates whether
the LLM represents the broader group. Obviously,
the more annotators, the better, as this increases the
reliability, reduces the influence of individual biases, and provides a more robust consensus signal
for comparison.

**Q: What if I have annotations from a single hu-**
**man annotator?**
**A:** Since our procedure requires at least two annotators, we recommend recruiting additional annotators for the alt-test. However, if the single annotator
is an expensive expert (or you trust their annotations) and cannot recruit others at the same expertise level, you can instead recruit lower-quality
annotators and test who better represents the expert:
the LLM or the newly recruited annotators. We refer to this as the single-expert scenario and provide
a detailed discussion on adjusting our procedure in
Appendix C.2.

**Q: How do I select the** _ε_ **value?**
**A:** We discuss this topic in detail in §B.1. Note that
_ε_ is the cost-benefit hyperparameter, where higher
values indicate greater efficiency advantages of the
LLM. As a rule of thumb, for expert annotators
(expensive, sometimes inaccessible), set _ε_ = 0 _._ 2.
For skilled annotators (e.g., undergraduate students,
trained workers, etc.), set _ε_ = 0 _._ 15. For crowdworkers, set _ε_ = 0 _._ 1.

**Q: How many instances should I annotate?**
**A:** We discuss this topic in detail in §5.1. To ensure the normality assumption of the t-test holds,

16065

you should have at least 30 instances. Our analysis shows that annotating between 50 and 100
instances is sufficient in most cases. Obviously,
the more annotated instances, the better, as this
increases the statistical power of the t-test and the
likelihood of the LLM passing the alt-test.

**Q: What if I have fewer than 30 annotated in-**
**stances per annotator?**
**A:** In this case, the normality assumption of the
t-test does not hold, so a non-parametric test, such
as the Wilcoxon signed-rank test, should be used
instead. Still, we strongly recommend having annotators label additional instances. See the next
question for an alternative approach.

**Q: I have two sets of human annotators.** **Can I**
**combine annotators from the first set with the**
**second set to increase the number of instances**
**per annotator?**
**A:** If you have two separate sets of annotators who
annotated different, non-overlapping instances, you
can artificially increase the number of instances per
annotator by pairing them across sets. For example,
suppose Set 1 consists of three annotators who annotated 20 instances, and Set 2 consists of another
three annotators who annotated a different set of
20 instances. You can combine an annotator from
Set 1 with an annotator from Set 2, treating them
as a single “combined annotator” with 40 instances.
To improve robustness, you can form multiple such
pairs and report the average winning rate across
different pairing combinations.
While this approach can increase the number of
annotated instances per annotator, it is not ideal.
The best practice is still to annotate more instances.
Combining annotators like this may also increase
the variance of the statistics (since we combine
instances annotated by different distributions). This
could lead to higher p-values, making the LLM fail.

**Q:** **What** **if** **I** **care** **about** **ranking** **rather** **than**
**exact scores?**
**A:** In some cases, the exact match between LLM
predictions and human annotations may not be as
important as the relative ordering of instances. For
example, if the goal is to ensure that higher-scored
instances by humans are also ranked higher by the
LLM. To evaluate this, we can adapt our procedure
to operate on ranks instead of raw scores. Specifically, we create a separate ranked list for each
human annotator and the LLM by assigning ranks
to instances based on their annotated scores (e.g.,
the lowest score gets rank 1). We then apply our

procedure to these ranks, replacing the original annotations. The alignment scoring function can be
negative RMSE, computed for each instance based
on the difference between its rank assigned by the
LLM and its rank assigned by the human annotator.

**Q: What if I have a skewed label distribution?**
**A:** In Appendix C.1, we discuss modifications to
our procedure to account for label imbalance.

**Q: How to test if the LLM can be used in several**
**environments or domains?**
**A:** When evaluating whether an LLM-as-a-judge
can be used across multiple environments or domains, it is important to evaluate it in each setting
independently while also controlling for the overall
False Discovery Rate (FDR). For example, suppose
we have five domains, each with three human annotators, resulting in 15 comparisons between the
LLM and humans. The FDR-controlling procedure
should be applied to the 15 p-values to ensure statistical rigor. Additionally, the winning rate should
be computed separately for each environment, and
the results should be summarized as:
_“The LLM passes the alt-test in X out of 5 domains.”_
In cases of hundreds of environments, collecting labeled data from at least three annotators per
environment may be impractical. This remains an
open challenge, but it offers promising directions
for future work, such as sampling representative
environments rather than testing all of them.

**Q:** **How** **to** **test** **who** **better** **represents** **human**
**experts?** **LLMs or crowd-workers?**
**A:** We discuss this scenario in Appendix C.2.

**Q: How to test whether LLMs outperform hu-**
**mans?** (and not whether they can replace them)?
**A:** We discuss this scenario in Appendix C.5.

**Q: What if I trust one annotator more than the**
**others?**
**A:** In Appendix C.3, we discuss simple modifications to our procedure to account for variations in
annotator quality.

**B** **Discussion**

The goal of this section is to discuss factors that influence the outcomes of the alt-test: the number of
annotated instances (which was already discussed
in §5.1), the value of the cost-benefit trade-off hyperparameter _ε_ (§B.1), and the profile of the human
annotators against whom we compare the LLM
(§B.2). In addition, we also present a case study
analysis of the SummEval dataset (§B.3).

16066

LGBTeen (Experts)

0.1 0.0 0.1 0.2 0.3 0.4

10K Prompts (Skilled)

0.1 0.0 0.1 0.2 0.3 0.4

MT-Bench (Experts)

0.1 0.0 0.1 0.2 0.3 0.4

CEBaB-S (Crowd-workers)

0.1 0.0 0.1 0.2 0.3 0.4

Framing (Skilled)

0.1 0.0 0.1 0.2 0.3 0.4

Lesion (Skilled)

0.1 0.0 0.1 0.2 0.3 0.4

CEBaB-A (Crowd-workers)

0.1 0.0 0.1 0.2 0.3 0.4

KiloGram (Crowd-workers)

0.1 0.0 0.1 0.2 0.3 0.4

1.0

0.8

0.6

0.4

0.2

0.0

1.0

0.8

0.6

0.4

0.2

0.0

WAX (Crowd-workers)

0.1 0.0 0.1 0.2 0.3 0.4

SummEval (Experts)

0.1 0.0 0.1 0.2 0.3 0.4

= 0.5 Gemini-Flash Gemini-Pro GPT-4o-mini GPT-4o

Figure 3: **Analysis of the Impact of Different** _ε_ **Values:** The x-axis represents different _ε_ values, while the y-axis
shows the winning rate _ω_ for four LLMs. If _ω_ _≥_ 0 _._ 5 (red line with triangles), the LLM passes the test, indicating it
is a comparable alternative to human annotators when considering the cost-benefit tradeoff represented by _ε_ . The
annotator types are stated next to the dataset names.

**B.1** **The Cost-benefit Hyperparameter**

We wish to use LLMs instead of human annotators since they offer a much cheaper, faster, and
less labor-intensive alternative. Therefore, we incorporated a cost-benefit hyperparameter into our
procedure, _ε_, which lowers the necessary threshold the LLM must exceed (i.e., _ρ_ _[h]_ _j_
alt-test. Generally, higher values of _[−]_ _[ε]_ _ε_ [) to pass the] are recommended when the cost and labor savings provided
by the LLM are substantial. For instance, this applies when human annotators are highly expensive,
require extensive and prolonged training, or when
the task is time-consuming or particularly challenging (e.g., annotating complex relationships within
lengthy documents). Conversely, smaller values of
_ε_ are more appropriate for simple annotation tasks
that untrained crowd-workers can complete.
To explore the relationship between different _ε_
values and the outcomes of the alt-test, as well
as to provide guidelines for setting these values,
we analyze the effect of _ε_ on the winning rate _ω_
of four LLMs, as shown in Figure 3. The strong
monotonic increasing relationship between _ε_ and _ω_,
as presented by our analysis, enables us to identify
the effective range of _ε_, which lies between 0.05
and 0.3. For _ε_ _>_ 0 _._ 3, all LLMs achieve _ω_ _≥_ 0 _._ 5
on every dataset (except SummEval, and GeminiPro in KiloGram) and pass the test. In contrast, for
_ε \<_ 0 _._ 05, all LLMs achieve _ω_ _\<_ 0 _._ 5 on all datasets
(except CEBaB-S) and fail the test.
From this analysis, we derive practical guidelines for selecting appropriate _ε_ values. First and
foremost, any value can be valid if the researcher
reasonably justifies their choice. This justification

may involve several aspects, including the cost and
effort of the annotation, the expertise of the annotators, the cost of annotation mistakes (which
varies based on the application and domain), and
the centrality of LLM annotations to the study.
As a rule of thumb, we recommend setting _ε_ to
0.2 when the annotators are trusted experts and 0.15
when they are skilled annotators (e.g., undergraduate students or trained workers). If the annotators
are crowd workers, _ε_ should be set to 0.1. In either
case, the quality of the annotators must be high
enough to ensure reliable annotations, as discussed
in the following subsection. In our experiments,
we selected _ε_ values based on the type of annotators (as indicated in Table 1 and Figure 3) and the
recommendations above.

**B.2** **The Human Annotators Profile**

Recall that our procedure aims to justify replacement if _the LLM aligns more closely with the col-_
_lective distribution than an individual does_, where
the collective distribution approximates the gold
label distribution. This collective distribution is the
most reliable and authoritative benchmark when
the annotators are experts. Accordingly, we recommend using expert annotators whenever possible
and, at the very least, highly trained crowd-workers.
If researchers themselves are experienced with the
task, they can serve as annotators.
In §C, we examine advanced topics related to human annotators. In §C.2, we address the scenario
of a single expert annotator and propose a simple
modification to our procedure. This scenario is
particularly relevant when only one expert is avail

16067

able due to limited accessibility or the high cost of
their annotations. This single expert annotates a
small subset of instances, and their annotations are
considered the gold labels (i.e., there is no collective distribution in this scenario). Our modification
compares the LLM against non-experts to determine whether the LLM aligns more closely with
the single expert than a non-expert does.
Additionally, in §C.3, we propose a modification to our procedure that incorporates a quality
score for each human annotator. This score can
be derived from various sources, such as qualification tests, and allows researchers to account for
annotator expertise and reliability differences.
In §C.4, we address the unique challenges of
subjective annotation tasks, where minority opinions may carry importance. For example, in hate
speech and offensive language detection, it is often
a single sensitive annotator, frequently from an underrepresented group, who identifies the offensive
content and deviates from the majority label. In
such cases, we aim to adapt our method to account
for and emphasize minority votes.
Finally, many studies aim not to use LLMs for
annotations or judgments but to evaluate whether
LLMs outperform humans. For example: _“Chat-_
_GPT Out-scores Medical Students on Clinical Care_
_Exam Questions”_ (Hadhazy, 2023). In these cases,
gold labels (e.g., exam answers) are available and
are used for benchmarking. Moreover, we set _ε_ = 0
because there is no need to penalize humans. In
§C.5, we discuss adapting the alt-test to rigorously
answer if LLMs outperform humans.

**B.3** **Case study:** **SummEval**

Table 2 reveals an anomaly in the SummEval
dataset: Mistral-v3, the open-source LLM,
achieves the highest _ρ_ . Interestingly, Mistral’s traditional measure score (Pearson’s correlation) is
low (0.12). This discrepancy warrants further investigation. As shown in Table 5 in the Appendix,
Mistral passes the test only for the Consistency aspect, with _ρ_ = 0 _._ 87, much higher than other LLMs
(around 0.45).
First, this demonstrates why each aspect should
be tested separately. Second, Table 6 in the Appendix, which reports the annotation distributions
for SummEval, explains why Mistral’s _ρ_ is so high:
human annotations for Consistency are highly
skewed, with the score ‘5’ assigned 89% of the
time. The only LLM with a similarly skewed prediction distribution is Mistral. Other LLMs predict

‘5’ only about 30% of the time. However, as shown
by Table 6, few-shot helps LLMs adjust and skew
their distributions, improving their alignment.
Noteworthy, unlike traditional measures (Pearson’s and Spearman’s correlations), our method
captures this nuance in alignment. In §C.1 of the
Appendix, we discuss label imbalance (like this
case) and propose an adjustment to our method
using Inverse Probability Weighting (IPW).

**C** **Advanced Topics**

**C.1** **Handling Imbalanced Labels**

In many annotation tasks, there is an issue of label
imbalance, where one class or category is disproportionately represented compared to others. For
instance, in the SummEval dataset’s "Consistency"
aspect, the majority vote scores are distributed as
follows: 1 : 0 _._ 02 _,_ 2 : 0 _._ 07 _,_ 3 : 0 _._ 02 _,_ 4 : 0 _._ 00 _,_ 5 : 0 _._ 89 .
_{_ _}_
This imbalance poses challenges for evaluation.
Traditional metrics like accuracy tend to favor annotators who predominantly assign ‘5’ as an annotator
who always chooses ‘5’ would achieve a high accuracy of 0.89. Conversely, correlation metrics may
penalize such annotators, even when their labels
have substantial overlap with others, as illustrated
in the code below:

1 **from** **scipy** . **stats** **import** **pearsonr**,

**spearmanr**

2

3 l1 = [1, 2, 3, 4] + [5] - 100

4 l2 = [5] - 100 + [4, 3, 2, 1]

5 **print** ( f 'Pearson: {pearsonr(l1, l2)

\[0\]:.2f}')

6 **print** ( f 'Spearman: {spearmanr(l1, l2)

\[0\]:.2f}')

Pearson: -0.03
Spearman: -0.04

Our procedure is not without flaws. For instance,
an LLM that consistently predicts ‘5’ would succeed and pass our test due to the high proportion
of ties (at least 89%). To address the issue of imbalanced labels, we propose a modification to our
procedure described below.
Let _Y_ = _y_ 1 _, y_ 2 _, . . ., yl_ represent the set of possible classes. We define _yi,j_ as the “gold” label for instance _xi_ when comparing the LLM with annotator
_hj_ . The “gold” label is given by _yi,j_ = _MVj_ ( _xi_ ),
where _MVj_ ( _xi_ ) is the majority vote label for _xi_
based on all annotators except _hj_ (ensuring the excluded annotator does not influence the gold label).
In the case of a single expert annotator (see §C.2),

16068

the gold label is defined as _yi,j_ = _h_ exp( _xi_ ). For
simplicity, we use _yi_ instead of _yi,j_ in the notation.
The idea is to weigh each instance annotated
by _hj_ with the inverse probability of its _MV_ label (this correction is known as inverse probability
weighting, IPW). The inverse probability of class
_y_, denoted by _πy,j_, is defined as:

I _j_
_πy,j_ = ~~�~~ _|_ _|_
_i_ I _j_ **[1]** _[{][MV][j]_ [(] _[x][i]_ [) =] _[ y][}]_
_∈_

where I _j_ is the set of instances annotated by _hj_,
and **1** _MVj_ ( _xi_ ) = _y_ is an indicator function that
_{_ _}_
gets one if the majority vote label of _xi_ is class
_y_, and zero otherwise. The difference between
the indicators _Wi,j_ _[f]_ [and] _[ W][ h]_ _i,j_ [is weighted to] _[ d]_ _i,j_ _[π]_ [=]

_πy,j_ ( _Wi,j_ _[h]_ _[−]_ _[W][ f]_ _i,j_ [)][.]
The formula of the weighted and balanced advantage probability, _ρ_ _[f]_ _j,π_ [, is:]

we propose a simple adjustment to our procedure,
and ask whether the LLM aligns more closely to **a**
**single expert** than **a non-expert human annota-**
**tor** does. This scenario represents a practical case
where an expert has annotated a subset of examples,
but more annotations are required. To continue, the
researcher must decide: Should the remaining annotations be completed by the LLM or by recruiting
a non-expert annotator? The adjustment is applied
only to the formula for the alignment score:

_−_ RMSE( _f, xi,_ exp) = _−|f_ ( _xi_ ) _−_ _h_ exp( _xi_ )) _|_

ACC( _f, xi,_ exp) = **1** _{f_ ( _xi_ ) = _h_ exp( _xi_ ) _}_

SIM( _f, xi,_ exp) = sim( _f_ ( _xi_ ) _, h_ exp( _xi_ ))

_ρ_ _[f,π]_ _j_ =

~~�~~ _i∈_ I _j_ _[π][y]_ _i_ _[,j][W][i,j]_
_i∈_ I _j_ _[π][y]_ _i_ _[,j]_

This formulation ensures that the overrepresentation of certain classes is mitigated, allowing each
class to contribute equally to _ρ_ _[f,π]_ _j_ . Similarly, we

define _ρ_ _[h,π]_ _j_ and the difference random variable is

given by _d_ [¯] _[π]_ _j_ [=] _[ ρ]_ _j_ _[h,π]_ _−_ _ρ_ _[f,π]_ _j_ .
Since the new random variables are weighted
means, their variance is different, and the corresponding test statistics should be adjusted:

_d_ ¯ _[π]_ _j_
_t_ _[π]_ _j_ [=] _[−]_ _[ε]_

_[π]_

_s_ _[π]_ _j_ _[/]_ ~~_√_~~

_n_ _[π]_

Where _s_ _[π]_ _j_ [and the effective sample size] _[ n][π]_ [are:]

_s_ _[π]_ _j_ [=]

~~�~~

~~�~~ - - _n_ ~~�~~ ~~�~~ 2

- _i_ =1 _[π][y]_ _i_ _[,j]_ _di,j_ _dj_

~~�~~ _−_ [¯]
_i∈_ I _j_ _[π][y]_ _i_ _[,j]_

_n_ _[π]_ = ( [�] ~~�~~ _i∈_ I _j_ _[π][y]_ _i_ _[,j]_ [)][2]
_i_ I _j_ _[π]_ _y_ [2] _i,j_
_∈_

The rest of the procedure for computing the winning rate _ω_ and applying the FDR correction remains unchanged.

**C.2** **A Single Expert Annotator**

In many cases, researchers wish to annotate their
dataset using experts, however, expert annotations
are expensive, hence most often we have only one
expert to compare to. To address this scenario,

Note that this time, we compare _S_ ( _f, xi,_ exp)
against _{S_ ( _hj, xi,_ exp) _}j_ _[m]_ =1 [,] [where] _[{][h][j][}]_ _j_ _[m]_ =1 [rep-]
resent non experts. The methods for aggregating
the scores across the entire datasets to calculate _ρj_
and the winning rate _ω_ remain unchanged.

**C.3** **Incorporating Annotator Quality**

A key principle of our procedure is valuing the
perspectives of all annotators, and until this subsection, each perspective has been treated equally.
However, this can sometimes be a limitation, as not
all annotators have the same level of expertise. For
instance, the input of a more experienced or highly
trained crowd-worker should carry more weight
than that of a novice. In medical annotations, such
as analyzing lesion images, the opinion of an experienced dermatologist would naturally be more
reliable and respected than that of an intern.

In this subsection, we propose a modification to
our procedure that incorporates a quality score assigned to each human annotator. The quality score
can be derived from various sources, such as performance on a qualification test performed by the
crowd-workers or a subjective assessment by the
paper authors based on their judgment. Weighting
annotations based on an annotator’s quality score is
a well-established practice in the NLP community
(Inel et al., 2014; Uma et al., 2021; Plank, 2022).

Let _Qj_ represent the quality score of annotator _hj_ . This score is incorporated at two points
in our procedure. The first is in the formula
for the alignment score metric, _S_ ( _f, xi, j_ ), where
we assign greater weight to high-quality annotators. The modification is defined as follows:

16069

~~��~~
_k∈_ H _i_ \[ _−j_ ~~�~~ \] _[Q][k]_ [(] _[f]_ [(] _[x][i]_ [)] _[ −]_ _[h][k]_ [(] _[x][i]_ [))][2]

RMSE( _f, xi, j_ ) =

_−_ _−_

~~�~~
_k∈_ H _i_ \[ _−j_ \] _[Q][k]_

ACC( _f, xi, j_ ) =

SIM( _f, xi, j_ ) =

_k∈_ H _i_ \[ _−j_ ~~�~~ \] _[Q][k]_ **[1]** _[{][f]_ [(] _[x][i]_ [) =] _[ h][k]_ [(] _[x][i]_ [)] _[}]_

~~�~~
_k∈_ H _i_ \[ _−j_ \] _[Q][k]_

~~�~~
_k∈_ H _i_ \[ _−j_ \] _[Q][k]_

_k∈_ H _i_ \[ _−j_ ~~�~~ \] _[Q][k]_ [sim][(] _[f]_ [(] _[x][i]_ [)] _[, h][k]_ [(] _[x][i]_ [))]

The second point where quality scores can
be incorporated is in the winning rate formula.
Specifically, if the LLM outperforms a high-quality
annotator, this should contribute more significantly
to the winning rate. The modification is as follows:

_ω_ =

- _mj_ =1 _[Q][j]_ **[1]** _[{][H]_ [0] _[j]_ [is rejected] _[}]_

~~�~~ _m_
_j_ =1 _[Q][j]_

**C.4** **Subjective Annotation Tasks**

Subjective annotation tasks, such as those involving hate speech or offensive language, often lack
a single ground truth and may reflect diverse perspectives, especially from marginalized or underrepresented groups. Accordingly, minority opinions should be considered when determining labels
and assessing annotation quality in subjective tasks.
Next, we will specify three options that can help
address this issue.

**Label imbalance (Appendix C.1):** While subjective tasks may not traditionally fall under label
imbalance, our proposed solution involves penalizing instances based on their “gold label” (i.e.,
majority vote), such that majority-class instances
contribute less to the test. A similar approach can
be adapted for subjective tasks, for example, giving
more weight to instances where a single annotator
flags a problematic statement, even if it is not the
majority view.

**Annotator quality (Appendix C.3):** We discuss
incorporating annotator quality scores, such as in
cases where one annotator is an expert and another
is less experienced. This approach is also applicable to subjective tasks, for instance, by assigning
higher quality scores to more sensitive annotators
or those from minority demographics.

**Customize** **the** **alignment** **scoring** **function**
**(** _S_ ( _f, xi, j_ ) **):** The alignment scoring function
(e.g., accuracy for classification) can be customized
to fit the researcher’s needs. For example, one
might use a variant of accuracy suitable for hate

speech, e.g., giving more weight to specific hate
speech labels. The rest of the procedure remains
unchanged, making our method highly flexible and
easily adaptable.

**C.5** **Testing if LLMs Outperform Humans**

Many studies do not aim to use LLMs for annotations or judgments but instead evaluate whether
LLMs outperform humans. For instance, Schubert et al. (2023) assessed LLM performance on
neurology board–style examinations, where LLMs
answered 85.0% of questions correctly, surpassing
the mean human score of 73.8%. Similarly, Luo
et al. (2024) compared LLMs to human experts
in predicting neuroscience experiment outcomes,
finding that LLMs achieved an average accuracy
of 81.4%, outperforming human experts, who averaged 63.4%. In these cases, gold labels (test
answers or experiment outcomes) are available and
used to benchmark LLMs against humans.
While comparing the performance of LLMs to
humans and conducting hypothesis tests to determine the significance of performance differences
is a well-established approach (Dror et al., 2018),
our procedure can also be applied in these scenarios. To apply the alt-test, the modification follows
the approach outlined in the previous subsection
§C.2. Simply replace the single expert annotation,
_h_ exp( _xi_ ) with the gold label _y_ gold in the formula for
the alignment score. Moreover, researchers should
set _ε_ = 0 _._ 0 in this case, as the goal is to determine
whether the LLM outperforms humans, rather than
testing if it holds an advantage in annotation tasks
while considering the cost-benefit penalty.
The advantage of the alt-test is that it quantifies
the number of humans the LLM statistically outperforms. For example, consider a scenario where
the LLM achieves a score of 70 on an exam, while
three humans score 80, 80, and 20. A simple comparison of the mean would suggest that the LLM
outperforms humans. However, _ω_ offers a more
realistic assessment by setting the LLM’s winning
rate to 0.33. Furthermore, the alt-test addresses a
potential limitation of mean comparisons, where
the human mean may disproportionately reflect individuals who contributed more annotations.

**C.6** **The Benjamini-Yekutiali Procedure**

The Benjamini-Yekutieli (BY) procedure (presented in Algorithm 1) is a statistical procedure designed to control the false discovery rate (FDR) in
multiple hypothesis testing. It is particularly suited

16070

for scenarios where the test statistics of the different
null hypotheses are dependent. Unlike the simpler
Benjamini-Hochberg procedure, the BY method in1
troduces a correction factor, _cm_ = [�] _[m]_ _j_ =1 _j_ [, which]
accounts for dependency among hypotheses. This
ensures that the overall FDR remains at the desired
level _q_ . The procedure identifies the largest set
of hypotheses whose p-values are below adjusted
thresholds, rejecting these null hypotheses while
controlling the FDR. The BY procedure is widely
used in fields like genomics and machine learning,
where testing dependencies are common.

**Algorithm 1** Benjamini-Yekutieli (BY) Procedure

**Require:** p-values from _m_ hypothesis tests, desired FDR level _q_ (e.g., 0.05)

1: Sort the p-values in ascending order:
_p_ (1) _p_ (2) _. . ._ _p_ ( _m_ )
_≤_ _≤_ _≤_
2: **for** _i_ = 1 to _m_ **do**

3: Compute the adjusted threshold using:

- _If_ _S_ = RMSE _,_ _then_ _f_ _[∗]_ ( _xi_ ) =

_−_

_k∈_ H _i_ _[h][k]_ [(] _[x][i]_ [)]

_If_ _S_ = RMSE _,_ _then_ _f_ _[∗]_ ( _xi_ ) = _k∈_ HH _i_ _i_ _[k]_ _[i]_ _,_

_−_ _|_ _|_

_predicting the mean annotation for xi._

threshold( _i_ ) = _[i]_

_m_

_[×]_

_q_

~~�~~ _m_ 1
_j_ =1 _j_

4: **end for**

5: Find the largest _i_ such that _p_ ( _i_ ) threshold( _i_ )
_≤_

6: Reject null hypotheses corresponding to
_p_ (1) _, p_ (2) _, . . ., p_ ( _i_ )
7: **return** List of rejected null hypotheses

_In_ _both_ _cases,_ _the_ _optimal_ _LLM-as-a-judge_
_achieves an advantage probability of ρ_ = 1 _._

_Proof._ Let _hj_ be the excluded annotator.

**Case 1** _S_ = **ACC:** Let _MV_ ( _xi_ ) denote the majority vote for instance _xi_, defined as the label that
appears most frequently in the set _{hk_ ( _xi_ ) _}k∈_ H _i_ .
In the event of a tie, where more than one label
qualifies as the majority, _MV_ ( _xi_ ) is randomly
sampled from the tied labels. We now show that
_f_ ( _xi_ ) = _MV_ ( _xi_ ) is optimal.
If _hj_ ( _xi_ ) = _MV_ ( _xi_ ), then _f_ ( _xi_ ) = _hj_ ( _xi_ )
and therefore _Wi,j_ _[f]_ [=] [1][.] [Otherwise,] [if] _[h][j]_ [(] _[x][i]_ [)] [=]
_MV_ ( _xi_ ), then by the definition of _MV_ ( _xi_ ):
�� ��
_{ k_ _∈_ H _i_ : _hk_ ( _xi_ ) = _MV_ ( _xi_ ) _}_ _≥_
�� ��
_{ k_ _∈_ H _i_ : _hk_ ( _xi_ ) = _hj_ ( _xi_ ) _}_

Note that if there is a single majority label, the set
on the left (top) is strictly larger than the set on the
right (bottom). If there is no single majority label, it
may be a tie in which _hj_ ( _xi_ ) appears with the same
frequency as the (randomly sampled) _MV_ ( _xi_ ).
Once we exclude _hj_ from both sets, the size of
the left set remains unchanged (since _MV_ ( _xi_ ) =
_̸_
_hj_ ( _xi_ ), _hj_ was never in the left set). However,
the right set loses one element (specifically _hj_ ).
Hence, ACC( _f, xi, j_ ) _>_ ACC( _hj, xi, j_ ) which implies _Wi,j_ _[f]_ [= 1][.]

**D** **The Optimal LLM-as-a-Judge**

In this subsection, we introduce a theorem that defines the optimal LLM-as-a-judge. The theorem
identifies the function that maximizes alignment
with the collective distribution, achieving an advantage probability of _ρ_ = 1.
The optimal LLM-as-a-judge naturally depends
on the choice of the scoring function, _S_ ( _f, xi, j_ ).
For instance, if ACC (accuracy) is used as the metric,
the optimal LLM-as-a-judge is the one that predicts
the majority vote for each instance. Conversely, if
RMSE (root mean squared error) is used, the optimal
LLM-as-a-judge is the one that predicts the mean of
the annotations. This is formalized in the theorem:

**Theorem** **1** (Optimal LLM-as-a-Judge) **.** _For_ _a_
_given dataset, let S_ ( _f, xi, j_ ) _be the alignment scor-_
_ing function. The optimal LLM-as-a-judge, denoted_
_as f_ _[∗]_ ( _xi_ ) _, is defined as follows:_

- _If S_ = ACC _, then f_ _[∗]_ ( _xi_ ) = _MV_ ( _xi_ ) _, predict-_
  _ing the majority vote of the annotators for xi._

**Case 2** _S_ = _−_ **RMSE:** Let

_h_ ¯( _xi_ ) =

_k_ H _i_ _[h][k]_ [(] _[x][i]_ [)]
_∈_

_|_ H _i|_

be the mean value of the annotations for instance
_xi_ . We now show that _f_ ( _xi_ ) = _h_ [¯] ( _xi_ ) is optimal.
If _hj_ ( _xi_ ) = _h_ [¯] ( _xi_ ), then _f_ ( _xi_ ) = _hj_ ( _xi_ ), implying _Wi,j_ _[f]_ [= 1][.] [Otherwise,] _[ h][j]_ [(] _[x][i]_ [)] _[ ̸]_ [= ¯] _[h]_ [(] _[x][i]_ [)][.]
To show that RMSE( _f, xi, j_ ) _\<_ RMSE( _hj, xi, j_ )
(which implies _Wi,j_ _[f]_ [= 1][), we need to prove:]

( _h_ [¯] ( _xi_ ) _hk_ ( _xi_ )) [2] _\<_
_−_
_k∈_ H _i_ \[ _−j_ \]

( _hj_ ( _xi_ ) _hk_ ( _xi_ )) [2]
_−_
_k∈_ H _i_ \[ _−j_ \]

First, we recall that the arithmetic mean uniquely
minimizes the sum of squared errors over a set of

16071

real numbers. Formally, for any _c_ :

( _h_ [¯] ( _xi_ ) _hk_ ( _xi_ )) [2] _\<_
_−_
_k∈_ H _i_

( _c_ _hk_ ( _xi_ )) [2]
_−_
_k∈_ H _i_

By setting _c_ = _hj_ ( _xi_ ), it follows:

( _h_ [¯] ( _xi_ ) _hk_ ( _xi_ )) [2] _\<_
_−_
_k∈_ H _i_

_k∈_ H _i_

- �2
  _hj_ ( _xi_ ) _hk_ ( _xi_ )
  _−_

Second, note that

-

_k∈_ H _i_ �\[ _−j_ \]

_k∈_ H _i_

- _h_ ¯( _xi_ ) _hk_ ( _xi_ )�2 _\<_
  _−_

- _h_ ¯( _xi_ ) _hk_ ( _xi_ )�2 _\<_
  _−_

- �2
  _hj_ ( _xi_ ) _hk_ ( _xi_ ) =
  _−_

- _k∈_ H _i_

- �2
  _hj_ ( _xi_ ) _hk_ ( _xi_ )
  _−_

_k∈_ H _i_ \[ _−j_ \]

The first inequality holds because

```
  - _h_ ¯( _xi_ ) _hj_ ( _xi_ )�2 _>_ 0
```

_−_

given _hj_ ( _xi_ ) = _h_ [¯] ( _xi_ ). The second follows from
the minimization property of the mean. The final
equality is trivial since

```
  - �2
```

_hj_ ( _xi_ ) _hj_ ( _xi_ ) = 0
_−_

Therefore, _Wi,j_ _[f]_ [= 1][.]

**Conclusion:** We have demonstrated that in both
cases, setting _f_ _[∗]_ ( _xi_ ) as defined ensures _Wi,j_ _[f]_ [=] [1]

for any instance _xi_ . Consequently, _ρ_ _[f]_ _j_ [= 1][. Further-]
more, since this holds for any excluded annotator
_j_, it follows that _ρ_ = 1.

**E** **Datasets**

- **WAX** (Liu et al., 2022) - Prompt provided
  in Box G.1. We use the Relation Labeling
  task from the Word Association eXplanations
  (WAX) dataset. In this task, MTurk annotators were presented with two words—a cue
  word and an associated word (e.g., _shark_ and
  _sharp_ ), along with an explanation (e.g., “shark
  teeth are sharp”). The annotators labeled the

16072

relation between the two associated words
based on the given explanation, selecting from
16 predefined relation types. We included
only items that were annotated by at least five
crowd workers.

- **SummEval** (Fabbri et al., 2021) - Prompt
  provided in Box G.9. This dataset includes
  human evaluations of summaries generated
  by 16 neural summarization models applied
  to 100 documents from the CNN/DailyMail
  test set. We focused on expert annotations
  (authors of summarization papers) collected
  for four dimensions: coherence, consistency,
  fluency, and relevance. The annotators rated
  summaries on a Likert scale from 1 to 5, with
  higher scores indicating better quality.

- **LGBTeen** (Lissak et al., 2024) – Prompt provided in Box G.2. Three expert annotators
  evaluated responses from humans and various LLMs to queries from queer youth, extracted from the r/LGBTeen subreddit. Each
  response was assessed using a ten-question
  questionnaire designed to evaluate desirable
  traits, such as inclusiveness, sensitivity, and
  openness (see Box G.3). Responses were categorized as ‘Yes,’ ‘Partially,’ ‘No,’ or ‘Irrelevant’. We kept only responses that were annotated by at least two annotators.

- **MT-Bench** (Zheng et al., 2024b) - Prompt
  provided in Box G.4. MT-Bench is a dataset
  consisting of 80 manually crafted multi-turn
  questions designed to evaluate the conversational and instruction-following abilities of
  LLMs. The dataset covers eight categories
  of prompts, such as writing, reasoning, math,
  and coding. Expert annotators, including the
  paper’s authors and graduate students with expertise in the relevant categories, evaluated
  responses from LLMs by assessing 20 multiturn questions conversation. For each question, annotators selected the better response
  between two competing LLM responses or
  marked it as a tie. We included only items
  annotated by at least two annotators and annotators who evaluated more than 30 items.

- **Lesion** (Cheplygina and Pluim, 2018) Prompt provided in Box G.11. This dataset
  includes images of skin lesions from the ISIC
  2017 challenge (Codella et al., 2018) that

undergraduate students annotated during a
project on medical image analysis. Each image was annotated with five features: asymmetry (scale 0-2), irregularity of the border (0-2),
number of colors present (1-6), presence of
structures such as dots (0-2) and presence of
a blueish glow (0-2).

- **Framing** (Frermann et al., 2023) - Prompt
  provided in Box G.5. This dataset consists
  of articles on climate change annotated with
  22 yes/no questions about narrative framing.
  The questions are grouped into five framing
  categories: resolution, conflict, human interest, moral, and economic. The 22 questions
  and annotation guidelines are presented in
  Boxes G.6 and G.7. The annotations were performed by four on-site annotators with backgrounds in social and political sciences, who
  underwent an extensive training phase. We
  included only article-question pairs that were
  annotated by at least three annotators.

- **CEBaB** (Abraham et al., 2022) – Prompt provided in Box G.8. This large-scale dataset
  comprises restaurant reviews annotated by
  crowd workers. The workers labeled the sentiment of four aspects: Food, Service, Noise,
  and Ambiance. Each aspect was categorized
  as ‘Positive’, ‘Negative’ or ‘Unknown’. Additionally, star ratings were provided on a
  five-point scale. We use two variants of
  this dataset: _CEBaB-A_, which includes annotations for the four aspects, and _CEBaB-S_,
  which includes the star ratings. For each variant, we retained only items annotated by at
  least three annotators. We identified a subset
  of ten annotators with the highest overlap of
  annotated items (i.e., items annotated by the
  largest number of these ten annotators).

- **10K** **Prompts** [12] - Prompt provided in
  Box G.10. This dataset is part of a project by
  Argilla and HuggingFace and was created by
  collecting prompts from various sources. The
  annotators are members of the HuggingFace
  community tasked with ranking the quality of
  synthetic and human-generated prompts on a
  Likert scale from 1 to 5. We identified a set of
  13 annotators, each with at least 30 items also
  annotated by another annotator.

[12https://huggingface.co/datasets/](https://huggingface.co/datasets/data-is-better-together/10k_prompts_ranked)
[data-is-better-together/10k_prompts_ranked](https://huggingface.co/datasets/data-is-better-together/10k_prompts_ranked)

- **KiloGram** (Ji et al., 2022) – Prompt provided
  in Box G.12. This dataset includes thousands
  of tangram images (see an example in Figure 4), annotated by MTurk workers. Each
  annotator provided a short free-text description of what the tangram shape looks like.
  For computing similarity between annotations,
  we use cosine similarity applied to representations extracted by a SentenceTransformer
  model. Note that we tested various SentenceTransformer models based on the HuggingFace STS English leaderboard [13], and the results presented in Table 4. We decided to
  report the results using ‘e5-large-v2’. [14]

Figure 4: Example of a tangram from the KiloGram
dataset with corresponding free-text human annotations.

|Col1|all-MiniLM-L6-v2|e5-large-v2|
|---|---|---|
|Humans<br>Gemini-Flash<br>Gemini-Pro<br>GPT-4o<br>GPT-4o-mini|Sim<br>WR\_ ω\_<br>WP\_ ρ\_<br>0.28<br>–<br>–<br>0.28<br>0.42<br>**0.56**<br>0.26<br>0.14<br>0.49<br>0.27<br>0.3<br>0.50<br>0.25<br>0.14<br>0.46|Sim<br>WR\_ ω\_<br>WP\_ ρ\_<br>0.78<br>–<br>–<br>0.79<br>0.66<br>**0.61**<br>0.77<br>0.08<br>0.43<br>0.78<br>0.2<br>0.53<br>0.78<br>0.16<br>0.49|
||**UAE-Large-V1**|**GIST-Embedding-v0**|
|Humans<br>Gemini-Flash<br>Gemini-Pro<br>GPT-4o<br>GPT-4o-mini|Sim<br>WR\_ ω\_<br>WP\_ ρ\_<br>0.51<br>–<br>–<br>0.51<br>0.32<br>**0.53**<br>0.50<br>0.16<br>0.48<br>0.49<br>0.12<br>0.43<br>0.48<br>0.04<br>0.41|Sim<br>WR\_ ω\_<br>WP\_ ρ\_<br>0.65<br>–<br>–<br>0.66<br>0.62<br>**0.57**<br>0.64<br>0.0<br>0.42<br>0.65<br>0.32<br>0.53<br>0.65<br>0.32<br>0.52|

Table 4: **Kilogram – Different Embeddings Models:**
Sim is the average cosine similarity between the embeddings. _ω_ is calculated with _ε_ = 0 _._ 1. Bold values
indicate the best-performing LLM according to _ρ_ and a
green background highlights a _ω_ higher than 0.5.

[13https://huggingface.co/spaces/mteb/](https://huggingface.co/spaces/mteb/leaderboard)
[leaderboard](https://huggingface.co/spaces/mteb/leaderboard)

[14https://huggingface.co/intfloat/e5-large-v2](https://huggingface.co/intfloat/e5-large-v2)

16073

**F** **Additional Results**

|Col1|Col2|SummEval — m|m = 3, n = 1600, ε = 0.2|2|Col6|
|---|---|---|---|---|---|
||**Coherence**|**Consistency**|**Fluency**|**Relevance**||
|Gemini-Flash<br>Gemini-Pro<br>GPT-4o<br>GPT-4o-mini<br>Llama-3.1<br>Mistral-v3|Pears<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.38<br>0.67<br>0.64<br>0.40<br>0.67<br>0.66<br>0.47<br>1.0<br>**0.75**<br>0.42<br>1.0<br>**0.75**<br>0.36<br>1.0<br>0.70<br>0.17<br>0.33<br>0.58|Pears<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.54<br>0.0<br>0.51<br>0.59<br>0.0<br>0.32<br>0.62<br>0.0<br>0.44<br>0.53<br>0.0<br>0.46<br>0.52<br>0.0<br>0.68<br>0.10<br>1.0<br>**0.87**|Pears<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.31<br>0.0<br>0.16<br>0.19<br>0.0<br>0.15<br>0.43<br>0.0<br>0.21<br>0.36<br>0.0<br>0.21<br>0.26<br>0.0<br>0.2<br>0.16<br>0.0<br>**0.48**|Pears<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.34<br>0.0<br>0.54<br>0.34<br>0.67<br>0.63<br>0.37<br>0.0<br>0.50<br>0.42<br>1.0<br>**0.76**<br>0.38<br>1.0<br>0.74<br>0.16<br>0.33<br>0.56||

|Col1|Col2|Lesion — m =|= 6, n = 100, ε = 0.15|Col5|Col6|
|---|---|---|---|---|---|
||**Asymmetry**|**Blue**|**Border**|**Color**|**Dermo**|
|Gemini-Flash<br>Gemini-Pro<br>GPT-4o<br>GPT-4o-mini|Pears<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.36<br>0.00<br>0.52<br>0.32<br>0.17<br>**0.74**<br>0.39<br>0.00<br>0.57<br>0.15<br>0.17<br>0.65|Pears<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.55<br>1.0<br>0.91<br>0.58<br>1.0<br>**0.95**<br>0.64<br>1.0<br>0.91<br>0.49<br>1.0<br>0.93|Pears<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.15<br>0.0<br>0.61<br>0.17<br>0.0<br>**0.72**<br>-0.02<br>0.0<br>0.21<br>0.01<br>0.0<br>0.57|Pears<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.63<br>1.0<br>0.89<br>0.56<br>1.0<br>**0.85**<br>0.59<br>0.83<br>0.81<br>0.60<br>0.67<br>0.75|Pears<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.27<br>0.0<br>0.63<br>0.19<br>0.5<br>**0.78**<br>0.24<br>0.0<br>0.59<br>0.32<br>0.5<br>0.77|

|Col1|Col2|LGBTeen — m|m = 4, n = 88, ε = 0.2|Col5|Col6|
|---|---|---|---|---|---|
||**Q1 Inclusiveness**|**Q2 Sensitivity**|**Q3 Validation**|**Q4 Mental**|**Q5 Personal**|
|Gemini-Flash<br>Gemini-Pro<br>GPT-4o<br>GPT-4o-mini<br>Llama-3.1<br>Mistral-v3|Acc<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.78<br>0.0<br>0.79<br>0.82<br>0.0<br>0.84<br>0.83<br>0.0<br>0.82<br>0.80<br>0.0<br>0.80<br>0.88<br>0.75<br>**0.87**<br>0.84<br>0.0<br>0.86|Acc<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.81<br>0.75<br>0.90<br>0.61<br>0.25<br>0.76<br>0.77<br>0.75<br>0.90<br>0.81<br>0.75<br>**0.93**<br>0.81<br>0.75<br>0.89<br>0.82<br>0.75<br>0.90|Acc<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.66<br>0.0<br>0.74<br>0.53<br>0.0<br>0.59<br>0.74<br>0.5<br>**0.82**<br>0.67<br>0.25<br>0.73<br>0.70<br>0.0<br>0.75<br>0.74<br>0.25<br>**0.82**|Acc<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.38<br>0.00<br>0.66<br>0.48<br>0.25<br>**0.77**<br>0.51<br>0.00<br>0.70<br>0.50<br>0.00<br>0.69<br>0.40<br>0.00<br>0.70<br>0.49<br>0.00<br>0.68|Acc<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.59<br>0.5<br>0.86<br>0.52<br>0.0<br>0.78<br>0.48<br>0.25<br>0.76<br>0.47<br>0.0<br>0.75<br>0.61<br>0.5<br>**0.82**<br>0.38<br>0.0<br>0.72|
||**Q6 Networks**|**Q7 Resources**|**Q8 Safety**|**Q9 Authenticity**|**Q10 Completeness**|
|Gemini-Flash<br>Gemini-Pro<br>GPT-4o<br>GPT-4o-mini<br>Llama-3.1<br>Mistral-v3|Acc<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.38<br>0.0<br>0.67<br>0.41<br>0.0<br>0.70<br>0.57<br>0.5<br>**0.78**<br>0.48<br>0.0<br>0.71<br>0.48<br>0.0<br>0.63<br>0.47<br>0.0<br>0.69|Acc<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.58<br>0.0<br>**0.69**<br>0.49<br>0.0<br>0.62<br>0.58<br>0.0<br>0.65<br>0.57<br>0.0<br>**0.69**<br>0.38<br>0.0<br>0.57<br>0.22<br>0.0<br>0.44|Acc<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.34<br>0.0<br>0.58<br>0.18<br>0.0<br>0.47<br>0.69<br>0.25<br>0.87<br>0.59<br>0.5<br>0.86<br>0.51<br>0.0<br>0.78<br>0.73<br>0.75<br>**0.89**|Acc<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.40<br>0.0<br>0.64<br>0.33<br>0.0<br>0.59<br>0.64<br>0.25<br>**0.77**<br>0.59<br>0.0<br>0.72<br>0.20<br>0.0<br>0.49<br>0.66<br>0.25<br>0.71|Acc<br>WR\_ ω\_<br>AP\_ ρ\_<br>0.48<br>0.0<br>0.62<br>0.33<br>0.0<br>0.53<br>0.39<br>0.0<br>0.66<br>0.42<br>0.0<br>0.69<br>0.53<br>0.0<br>0.69<br>0.48<br>0.0<br>**0.79**|

Table 5: Results for different annotation aspects in SummEval, Lesion and LGBTeen datasets. _m_ and _n_ are the
number of annotators and instances, respectively. Acc is the accuracy with the majority vote, and Pears is the
average Pearson correlation. WR is the winning rate ( _ω_ ), and AP is the average advantage probability ( _ρ_ ). Bold
values indicate the best-performing LLM according to _ρ_, and a green background highlights _ω_ _≥_ 0 _._ 5.

|Col1|Coherence|Consistency|Fluency|Relevance|
|---|---|---|---|---|
|Humans|1<br>2<br>3<br>4<br>5<br>.05<br>.14<br>.36<br>.20<br>.25|1<br>2<br>3<br>4<br>5<br>.02<br>.07<br>.02<br>.00<br>.89|1<br>2<br>3<br>4<br>5<br>.00<br>.02<br>.08<br>.02<br>.88|1<br>2<br>3<br>4<br>5<br>.02<br>.05<br>.27<br>.44<br>.22|
|Llama-3.1<br>Mistral-v3|.02<br>.29<br>.32<br>.24<br>.13<br>.00<br>.00<br>.01<br>.57<br>.42|.02<br>.04<br>.09<br>.27<br>.58<br>.00<br>.00<br>.02<br>.01<br>.97|.10<br>.30<br>.17<br>.34<br>.09<br>.00<br>.00<br>.04<br>.59<br>.37|.01<br>.18<br>.20<br>.41<br>.20<br>.00<br>.00<br>.01<br>.04<br>.95|
|Gemini-Flash<br>+ 4-shots<br>Gemini-Pro<br>+ 4-shots|.04<br>.39<br>.52<br>.05<br>.00<br>.02<br>.16<br>.53<br>.25<br>.04<br>.01<br>.46<br>.42<br>.11<br>.00<br>.00<br>.14<br>.27<br>.46<br>.13|.02<br>.03<br>.19<br>.37<br>.39<br>.00<br>.03<br>.08<br>.09<br>.80<br>.02<br>.05<br>.16<br>.59<br>.18<br>.01<br>.05<br>.09<br>.11<br>.74|.00<br>.18<br>.54<br>.27<br>.01<br>.00<br>.01<br>.07<br>.24<br>.68<br>.00<br>.16<br>.77<br>.07<br>.00<br>.00<br>.00<br>.17<br>.21<br>.62|.03<br>.36<br>.53<br>.08<br>.00<br>.02<br>.10<br>.53<br>.31<br>.04<br>.00<br>.23<br>.61<br>.14<br>.02<br>.01<br>.11<br>.30<br>.39<br>.19|
|GPT-4o<br>+ 4-shots<br>GPT-4o-mini<br>+ 4-shots|.01<br>.20<br>.45<br>.34<br>.00<br>.01<br>.07<br>.21<br>.52<br>.19<br>.01<br>.20<br>.46<br>.33<br>.00<br>.01<br>.11<br>.27<br>.57<br>.04|.01<br>.12<br>.09<br>.44<br>.34<br>.01<br>.06<br>.08<br>.19<br>.66<br>.00<br>.06<br>.13<br>.50<br>.31<br>.00<br>.00<br>.05<br>.11<br>.84|.01<br>.09<br>.42<br>.45<br>.03<br>.00<br>.01<br>.11<br>.30<br>.58<br>.00<br>.10<br>.45<br>.44<br>.01<br>.00<br>.01<br>.08<br>.27<br>.64|.03<br>.45<br>.45<br>.07<br>.00<br>.00<br>.08<br>.39<br>.43<br>.10<br>.00<br>.11<br>.48<br>.40<br>.01<br>.00<br>.07<br>.21<br>.58<br>.14|

Table 6: Distributions of human and LLM annotations (scores between 1 to 5) for different aspects of SummEval.
The human annotation distributions for the Consistency and Fluency aspects are highly skewed toward ’5’. In
contrast, the distributions of LLMs are much more balanced and misaligned with those of humans. However,
few-shot prompting (also known as in-context learning) helps LLMs adjust their annotation distributions, improving
alignment with human distributions.

16074

**G** **Prompts**

16075

16076

16077

16078

16079

16080

16081
