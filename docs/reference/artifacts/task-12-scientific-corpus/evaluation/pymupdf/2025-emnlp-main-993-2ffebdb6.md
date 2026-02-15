# **Humans Hallucinate Too: Language Models Identify and Correct** **Subjective Annotation Errors With Label-in-a-Haystack Prompts**

**Georgios Chochlakis, Peter Wu, Arjun Bedi,**
**Marcus Ma**, **Kristina Lerman**, **Shrikanth Narayanan**
University of Southern California

**Correspondence:** [chochlak@usc.edu](mailto:chochlak@usc.edu)

**Abstract**

Modeling complex subjective tasks in Natural
Language Processing, such as recognizing emotion and morality, is considerably challenging
due to significant variation in human annotations. This variation often reflects _reasonable_
differences in semantic interpretations rather
than mere noise, necessitating methods to distinguish between legitimate subjectivity and
error. We address this challenge by exploring _label_ _verification_ in these contexts using
Large Language Models (LLMs). First, we
propose a simple In-Context Learning binary
filtering baseline that estimates the _reasonable-_
_ness_ of a document-label pair. We then introduce the _Label-in-a-Haystack_ setting: the
query and its label(s) are included in the demonstrations shown to LLMs, which are prompted
to predict the label(s) again, while receiving
task-specific instructions (e.g., emotion recognition) rather than label copying. We show how
the failure to copy the label(s) to the output
of the LLM are task-relevant and informative.
Building on this, we propose the **L** abel- **i** n- **a** **H** aystack **R** ectification ( _LiaHR_ ) framework for
subjective label correction: when the model
outputs diverge from the reference gold labels,
we assign the generated labels to the example
instead of discarding it. This approach can
be integrated into annotation pipelines to enhance signal-to-noise ratios. Comprehensive
analyses, human evaluations, and ecological
validity studies verify the utility of _LiaHR_ for
label correction. Code is available at [https:](https://github.com/gchochla/liahr)
[//github.com/gchochla/liahr.](https://github.com/gchochla/liahr)

**1** **Introduction**

In this work, we address the challenge of modeling
complex subjective tasks in natural language, captured in benchmarks such as for emotion recognition and moral foundation prediction. By “complex
subjective”, we refer to problems where multiple
(subjective) interpretations can be _reasonable_, and
there is often no single “correct” answer. In such

Figure 1: _Label-in-a-Haystack Rectification (_ _**LiaHR**_ _)_ :
The query also appears in the prompt as a demo. The
LLM is instructed to perform the actual task, as captured
by the label names. We leverage the failure to correctly
copy-paste the query’s label to flag the query-label pair,
for filtering or even correction based on the prediction.

cases, “ground” truth is substituted with crowd
truth (Aroyo and Welty, 2015), such as majority
vote. Previous work has also referred to these
settings as _survey_ _settings_ (Resnick et al., 2021),
where similarly “ground” truth is the wisdom of the
crowd. This stands in contrast to “objective” tasks
where we can define a correct answer and annotator
disagreement is generally viewed as error or noise.
The distinction is evident when looking at interannotator agreement in these settings (Mohammad
et al., 2018; Demszky et al., 2020), but also the

19637

_Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing_, pages 19637–19656
November 4-9, 2025 ©2025 Association for Computational Linguistics

utility of objectively correct responses compared
to disagreements in reinforcement learning with
verifiable rewards (Guo et al., 2025), for instance.
Therefore, whereas noise in objective labels
needs to be discarded and can be detected by looking at agreement between annotators, for subjective tasks, annotator disagreement may carry signal
rather than noise, reflecting differences in perspective or background. Therefore, conventional error
correction approaches based on agreement metrics
are not directly applicable. Instead, improving subjective modeling requires filtering variation due to
error in gold labels while preserving meaningful
disagreement (Booth and Narayanan, 2024).
To address this challenge, we propose a framework that uses LLMs for _error detection and correc-_
_tion_ in subjective annotations that respects different
perspectives. In this manner, we can maintain the
diversity of opinions in the data, while also maximizing the signal-to-noise ratio. Prior works in
these settings (Hovy et al., 2013; Swayamdipta
et al., 2020; Mokhberian et al., 2022) have relied
on training classifiers across entire datasets to identify unreliable labels based on model predictions
and inter-annotator disagreement. In contrast, our
approach leverages LLMs in a few-shot, online
setting to assess and even refine labels during annotation. We begin by introducing “reasonableness” labels as the simple baseline (Figure 16 in
the Appendix) to demonstrate how LLMs can be
catered to filtering explicitly instead of proxy filtering through classification. This binary indicator characterizes whether a document-label pair is
reasonable (i.e., plausible, as we do not necessarily adopt a right-wrong split). We can, thereafter,
prompt an LLM to predict the reasonableness label
of a query document-label pair.
To achieve correction, we introduce the _Label-_
_in-a-Haystack_ task, shown in Figure 1, that leverages the biases of LLMs toward their prior knowledge (Shi et al., 2024; Chochlakis et al., 2024). In
this setting, the query and a candidate label are included in the prompt, and the model is instructed to
perform the task of the dataset (that is, not merely
to copy the label). Given the prediction of the LLM,
we simply check whether the model was able to
copy the labels from its prompt correctly. We refer
to this setting as **L** abel- **i** n- **a** - **H** aystack **R** ectification
( _LiaHR_ ), as the model generates alternatives when
it “disagrees” enough with the provided labels, effectively correcting unreasonable annotations.
To evaluate our proposed approaches, we first

propose, define and evaluate four proxy properties integral to subjective modeling: **Nonconfor-**
**mity**, **Diversity**, **Noise** **rejection**, and **Rectifica-**
**tion** . Then, we verify whether model decisions and
proposed alternatives align well with human judgments. Finally, to assess the ecological validity of
the filtering and correction proposed, we show that
the performance of BERT-based models (Devlin
et al., 2019) increases on the corrected datasets.
Our findings reveal that both the reasonableness
baseline and the _LiaHR_ framework can successfully verify and correct subjective labels. As such,
our proposed framework can be effectively used
_during_ (not after) the annotation process, and is
specifically catered to complex subjective settings.
We leverage its commonsense priors to correct the
labels, rejecting unreasonable annotations in context, reinforcing prior observations that in-context
learning in LLMs may rely more on _task recogni-_
_tion_ than _task learning_ (Min et al., 2022). Furthermore, by causally manipulating the prompt labels
to belong to in-group or out-group members (Dorn
et al., 2024), but without explicit mention of this
manipulation to the model, we show how _LiaHR_
can reliably pick up implicit cues from a few examples. Finally, we also show that aggregated labels are rejected at higher rates compared to individual annotators, corroborating previous findings (Chochlakis et al., 2025) of the unsuitability
of aggregation for subjective language tasks.

**2** **Related Work**

**2.1** **Viewpoint Diversity**

Many works have attempted to model individual annotator perspectives instead of the aggregate to capture their differing perspectives. Recently, Gordon
et al. (2022) fused Transformer features (Vaswani
et al., 2017) with annotator features that include
demographic factors, among others, to model individual perspectives. Demographic information has
also been fused into word embeddings by Garten
et al. (2019). In addition, systematic biases have
been assessed through rigorous annotations and
profiling (Sap et al., 2022). Other recent work has
tried to model annotators on top of common representations (Davani et al., 2022; Mokhberian et al.,
2023), and to decrease annotation costs online
based on disagreement (Golazizian et al., 2024).
Modeling annotators with LLMs has shown limited success due to LLM biases (Dutta et al., 2023;
Abdurahman et al., 2024; Hartmann et al., 2023).

19638

**2.2** **Error Detection**

Previously, error detection has been carried out in
a variety of ways and levels of intervention. One
research thread assumes a single correct answer per
item, and proceed to identify errors or “spammer”
annotators. Examples include the Dawid-Skene
algorithm (Dawid and Skene, 1979), MACE (Hovy
et al., 2013), and CrowdKit (Ustalov et al., 2021).
However, these methods fail the basic assumption
of our work, as they do allow difference in opinion, marginalizing idiosyncratic viewpoints, which
may otherwise be internally consistent (Chochlakis
et al., 2025). Similar approaches that allow for disagreement still assign scores per item and annotator
individually and not for separately for each pair,
like CrowdTruth (Dumitrache et al., 2018).
In another research thread, again as a postprocessing step, previous work has used trained
models on the dataset to assess the quality of the
labels, either directly, e.g., with dataset cartography (Swayamdipta et al., 2020; Mokhberian et al.,
2022), where each data point is mapped onto a 2D
space depending on the confidence and the accuracy of the predictions, or indirectly, e.g., with self
distillation (Stanton et al., 2021).
Label verification has also been explored online by using predictions from a model, such as
a Large Language Model (LLM), and checking
them against the annotations (Feng and Narayanan,
2024). However, this method trivially considers
differing perspectives invalid. Previous work has
also shown how the prior biases of LLMs ossify
their posterior predictions (Chochlakis et al., 2024),
which in turn leads to failures in accommodating different perspectives during regular inference.
This further narrows the breadth of subjective assessment we ideally want to capture and limits
our ability to potentially elicit different predictions
from LLMs in subjective settings. When iterating
in batches, verification checks cannot be automated
similar to the aforementioned post-processing step
due to the lack of sufficient data, so checks need to
be manual, such as analyzing disagreement or having annotators engage in consensus talks (Paletz
et al., 2023), significantly increasing costs. Liu
et al. (2023) showed that LLMs do not model ambiguity, an important component of disagreement.

**3** **Methodology**

First, it is important to provide some working definition of _reasonableness_ (and in turn, what a sub

jective task is). For our purposes, we consider a
document-label pair to be reasonable if and only if a
person who would annotate differently can nonetheless consider some reasoning process that leads to
that label valid. That is, if a human can agree that
a reasoning process is _valid_, _coherent_, and _faith-_
_ful_ (Jacovi and Goldberg, 2020) with respect to the
label, then that label is deemed reasonable [1] . We
present the general and intuitive description of our
methods in this section and a more mathematically
rigorous description in Appendix A.

**Reasonableness** **labels** We construct a dataset
dynamically, wherein our data consist of documentlabel pairs. As a proxy for reasonableness, the labels are either the gold label of the document from
the original dataset, or randomly sampled for unreasonable pairs. This setting is shown in Figure 16
in the Appendix. Each document can appear with
both types of labels. We sample the labels of another example from the dataset for unreasonable
pairs to maintain the label distribution.

**Label-in-a-Haystack** As shown in Figure 1, the
query and its candidate label are included in the
prompt as the first example, and the model is instructed to perform the task described by its labels.
However, due to inclusion of the label in the prompt
already, we essentially check whether the model
is able to copy-paste the query’s label onto its output. Given previous results about the collapse of
the posterior predictions of LLMs to the priors in
complex subjective tasks (Chochlakis et al., 2024),
we expect that in cases where the gold labels are
“judged” to be erroneous by the model, the copypasting will fail, flagging a label for further review.
In addition to this ability, this setting also allows us
to immediately get alternative labels for the example, a property that the baseline does not possess.
In this manner, we do not waste data by discarding
examples that are flagged by the model. We note
that when using random labels for the query document, we sample them from a random document in
the dataset, similar to the baseline.
Intuitively, this method exploits the reliance of
the model on its prior knowledge of the task. If a label has sufficiently “high probability” for a model a
priori, even if not its dominant prediction, then we
expect its presence in the prompt to “push” the posterior towards that label enough so that it prevails

1in the case of initial disagreement with a specific rationale, iterative refinement until agreement is achieved is valid,
assuming the reasoning remains faithful to the labels

19639

in the output. Therefore, only highly unreasonable labels are rejected by the model, leading to
higher precision in identifying errors. Note that the
performance of the model using In-Context Learning is rather poor for such tasks (Chochlakis et al.,
2024), resulting in poor precision with many false
negatives and therefore increased annotation costs.

**3.1** **Proxy Properties**

In this section, we define and present desirable
proxy properties that can be used as proxies for
the label filtering and correction ability that practitioners can use to guide model selection. Note
that since strictness is not required because of their
proximate nature, some of them are fuzzy and
heuristic.

**Nonconformity** : The model should flag
some dataset labels as unreasonable, but
only for a small percentage of examples.

This is the first requirement. Although “small”
is nebulous, the model should be copying the gold
labels significantly better compared to its performance as a classifier. Having a smaller gap to the
dataset’s labels indicates an ability to agree with
different perspectives, and it assumes that most of
the dataset has been annotated properly [2] .

**Diversity** : The model should accept different labels consistently.

Respecting different opinions is also an integral
property. Here, we also assume that most annotators have annotated most of the dataset properly [3] .
For this quality of the model, we can use annotations from different individuals and expect the
model to predict reasonableness or successfully
copy the labels at equally high rates for them all.

**Noise Rejection** : The model should assign reasonableness at random performance levels when using random labels.

That is to say, when asked to “verify” a random
label, the model should succeed only when the label “happens” to be reasonable, meaning random
levels of performance (though not exactly a random baseline, as more perspectives not present in
the data could also be valid). We measure this by

2in this assumption, we take for granted that annotators
have been screened, trained, attention-checked, etc. Namely,
we assume quality data collection
3we make the same assumptions as above

randomizing the label of the pair for the baseline or
the query label for _LiaHR_, and expect low success
rates of filtering or copying respectively.

**Rectification** : When _LiaHR_ is prompted
with random labels for the query, its alternative predictions should be closer to
the original, gold labels than the random
labels it was given.

This final property is a _LiaHR_ -specific constraint.
If the model is to not only identify unreasonable
labels, but also correct them, then when it is given
random labels for the query, its predictions should
be closer to the gold labels compared to those random labels. As a result, this can be measured by
calculating the similarity of the _LiaHR_ predictions
when _LiaHR_ is provided a random query label with
the original, gold labels, and comparing that with
the copy performance for the random labels, which
is equivalent to the similarity of the predictions to
the random labels. We expect successful models
to have the higher similarity to the gold labels. We
expect that priming the model with random labels
may cause it to fail to meet this precisely, so only
trends towards it are sought out.

**3.2** **Human Evaluations**

To validate our findings on the proxy properties,
we perform human evaluations in two settings:

**Reasonableness** We compare human assessment
of the reasonableness of the labels to the LLM’s
assessments. We use the chi-square test of independence of variables in a contingency table to
evaluate the significance of our results (with the
binary variable being reasonableness).

**Preference** We compare human preference for
_LiaHR_ predictions over the gold label. Significance
is calculated with a binomial test. We also compare to the regular ICL predictions to isolate the
effects of _LiaHR_ from the model’s classification
capabilities on these tasks.

**3.3** **Ecological Validity**

In addition to human evaluations, we train smaller
models on the labels derived from our filtering
pipelines. Namely, we examine (i) the Original labels, (ii) _LiaHR_ on the entire corpus (Replaced) or
only on the (trn) set, (iii) _LiaHR_ but used to filter
training example when copy-pasting is erroneous

19640

Baseline success rate on SemEval 2018 Task 1

1.0

0.8

0.6

0.4

0.2

0.0

1.0

1.00

0.75

0.50

0.25

0.00

1.00

0.75

0.50

0.25

0.00

1.00

0.75

0.50

0.25

0.00

Label-in-a-Haystack success rate on

SemEval 2018 Task 1

5 15 25 55 75
Shots

0.8

0.6

0.4

0.2

0.0

5 15 25 55 75
Shots

1.0

0.8

0.6

0.4

0.2

0.0

5 15 25 55 75
Shots

5 15 25 55 75
Shots

Figure 2: Success rate of copying the labels in _LiaHR_
on **SemEval** when using the gold and random labels
for the query in the prompt across various numbers of
demonstrations. We also show performance w.r.t. the
gold labels when using random query labels.

(Filtered), (iv) the _reasonableness_ baseline to filter out training examples (Bsl Filtered), (v) the
Predictions of the LLM with ICL.

**3.4** **Metrics**

Because the _LiaHR_ format is identical to classification, we use classification metrics to evaluate the
performance of copy-pasting and get a more nuanced picture of the predictions of the model. We
use Jaccard Score and Micro F1 for multilabel, and
accuracy and F1 for single-label cases.

**4** **Experiments**

**4.1** **Datasets**

**SemEval** **2018** **Task** **1** **E-c** **(SemEval;** **Moham-**
**mad** **et** **al.** **2018)** A multilabel emotion recognition benchmark containing annotations for 11
emotions: _anger_, _anticipation_, _disgust_, _fear_, _joy_,
_love_, _optimism_, _pessimism_, _sadness_, _surprise_, and
_trust_ . We use only the English subset.

**MFRC (Trager et al., 2022)** A multilabel moral
foundation corpus with annotations for six moral
foundations: _care_, _equality_, _proportionality_, _loy-_
_alty_, _authority_, and _purity_ . The dataset was released

Figure 3: _Baseline_ “reasonable” scores on **SemEval**
when using gold and random input-label pairs.

with annotator labels.

**GoEmotions (Demszky et al., 2020)** A multilabel emotion recognition benchmark with 27 emotions. For efficiency and conciseness, we pool the
emotions to the following seven “clusters” using hierarchical clustering: _admiration_, _anger_, _fear_, _joy_,
_optimism_, _sadness_, and _surprise_ . The dataset was
released with annotator labels.

**QueerReclaimLex** **(Dorn** **et** **al.,** **2024)** Singlelabel binary harm dataset, which contains various
templates populated with reclaimed LGTBQ+ slurs.
It contains two harm labels: assuming in-group and
out-group authors. Using one or the other without explicit mention, we can evaluate the **Diver-**
**sity** property with a known and controllable causal
factor. This setting serves as a stress test, since
reclaimed slurs in general are a documented failure
case for, e.g., toxicity classifiers (Sap et al., 2019;
Haimson et al., 2021; Sap et al., 2022), allowing
us to examine whether systematic biases in LLMs
influence their decisions in our framework. For the
same reasons, it is challenging because it includes a
realistic confounding factor: the interplay between
politeness guardrails and our desired behavior, as
slurs are explicitly included throughout the prompt.
We create splits to be as balanced as possible, but
also present ROC-AUC to avoid bias. Because the
labels are binary, we use the opposite label instead

19641

Baseline success rate on GoEmotions

1.0

0.8

0.6

0.4

0.2

0.0

1.0

1.00

0.75

0.50

0.25

0.00

1.00

0.75

0.50

0.25

0.00

1.00

0.75

0.50

0.25

0.00

Label-in-a-Haystack success rate on

GoEmotions

5 15 25 55 75
Shots

0.8

0.6

0.4

0.2

0.0

0.0

Shots

1.0

0.8

0.6

0.4

0.2

5 15 25 55 75
Shots

Shots

Figure 4: Success rate of copying the labels in _LiaHR_
on **GoEmotions** when using the gold and random labels
for the query in the prompt across various numbers of
demonstrations. We also show performance w.r.t. the
gold labels when using random query labels.

of randomizing the query label.

**4.2** **Implementation Details**

We use the 4-bit quantized versions of the
open-source LLMs through the _Hugging-_
_Face_ (Wolf et al., 2020) and bitandbytes
interface for _PyTorch_ . We use GPT-3.5 Turbo
(gpt-3.5-turbo), GPT-4 (gpt-4-turbo), and
GPT-4o (gpt-4o-mini), Llama-2 7B and
70B (meta-llama/Llama-2-#b-chat-hf),
and Llama-3 8B and 70B
(meta-llama/Meta-Llama-3-#B-Instruct).
We chose only finetuned models (Ouyang et al.,

2022. to avoid confounding factors. We use
      random retrieval of examples. We train _De-_
      _mux_ (Chochlakis et al., 2023) as the smaller model
      for ecological validity. When sampling random
      labels, we ensure at least one label is present (i.e.,
      we do not allow Nones because of their higher
      plausibility). Results for proxy properties are
      3 different seeds with 100 inference examples
      each. The entire corpus is used for training and
      evaluation of smaller models. Unless otherwise
      noted, we show 95% confidence interval around
      the mean. For more details, see Appendix B and C.

Figure 5: _Baseline_ “reasonable” scores on **GoEmotions**
when using gold and random input-label pairs.

**4.3** **Evaluating Proxy Properties**

The first step to applying these methods for label
verification is to show that copy-pasting can fail
in _LiaHR_, and that they indeed meet the desired
proxy properties. Throughout this section, when
presenting **success rates**, that refers to the amount
of copy-pasting that happened successfully. This
means that _when randomizing_ the labels, we still
count _whether_ _the_ _random_ _labels_ _are_ _generated_,
and therefore _lower scores on random labels_ represent more desirable behavior.

**SemEval** We present our results for all [4] models
in Figure 2 for _LiaHR_ and Figure 3 for the baseline. In Figure 2, we present the performance of
the model on the copy-paste task when using gold
(Query w/ gold) and random (Query w/ rand)
labels for the demo query, as well as the performance of the model on the gold labels when the
query label is random (and therefore the model has
not seen the test label for the query; Gold perf w/
rand). All results are shown for 5, 15, 25, 55, and
75 shot (to demonstrate scalability). For Figure 3,
we show the first two scenarios, where the docu

4some API-based models were deprecated during the
course of our experiments, so we skip them where they are
not available. For additional results, such as GPT-4, see Appendix D.

19642

ment is presented to the LLM with its paired label
(Gold pair) or a random label (Rand pair).
In _LiaHR_, we see clear evidence for our desired behavior in bigger and more capable models, specifically GPT-3.5, GPT-4o, and Llama-3
70b. These models seem to display all the properties we check for: **Nonconformity**, **Rectifica-**
**tion**, and **Noise rejection** . First, the success rate
with gold labels for the query is not perfect (meaning 1.0), yet it is significantly higher compared
to the same model’s performance on the benchmark (Chochlakis et al., 2024). This means that
the model does not conform to the gold labels completely, yet is greatly influenced by them in its
predictions (otherwise we would anticipate performance much closer to its “regular” predictions).
By meeting both these criteria, the aforementioned
models meet the **Nonconformity** property. Then,
when we use random labels instead of gold for the
query in the prompt, we see the success rate drop
dramatically compared to when gold labels are presented (that it, when comparing Query w/ gold
to Query w/ rand). This indicates that models
achieve the **Noise Rejection** property. Moreover, it
is interesting to see that, when random labels are
provided, the predictions match more closely the
gold labels (Gold perf w/ rand) than these random labels (Query w/ rand). Since this criterion
is met, the models achieve **Rectification** .
For the “reasonableness” baseline, we see that
only GPT-4o meets the criteria **Nonconformity**,
and **Noise rejection** [5] . While other models mostly
meet the **Noise Rejection** criterion, their success
rate is too low to qualify for **Nonconformity** . We
also notice that the success rate in all settings is
noticeably lower compared to _LiaHR_ .
Interestingly, when looking at smaller and less
capable models, we see that the models achieve
higher copy-paste performance, both with the
dataset labels and with random labels, and therefore
**Nonconformity** and **Noise Rejection** are only partially achieved. Consequently, when using random
query labels, their predictions are more similar to
these random labels compared to the dataset labels,
so the models do not display **Rectification** .

**GoEmotions** We show our results for _LiaHR_ in
Figure 4 and for the baseline in Figure 5. We notice that in GoEmotions, even GPT-4o struggles,
with the acceptance rates of random labels, as the

5 **Rectification** is not a potential property because the LLM
does not generate labels

|GoEmotions|Col2|Col3|Col4|Col5|Col6|
|---|---|---|---|---|---|
|||||||
|||||||
|||||||
|||||||
|||||||
|||||||

|MFRC|Col2|Col3|Col4|Col5|Col6|Col7|
|---|---|---|---|---|---|---|
||||||||
||||||||
||||||||
||||||||
|||||Ann0<br>|||
|||||~~Ann1~~<br>Ann2<br>~~Aggre~~|~~ate~~||
|||||Rando|m|m|
||||||||

Figure 6: Success rate of copying the labels of _LiaHR_ on
**GoEmotions** and **MFRC** with aggregate labels, random
labels, and annotator labels ( _Ann#_ ), shown for 15-shot
prompts. For GoEmotions, actual annotator IDs are:
Ann0 = 37, Ann1 = 4, Ann2 = 61. For MFRC: Ann0 = 0,
Ann1 = 1, Ann2 = 3.

_LiaHR_ **Reasonableness** **Preference**

Llama-3 70b 6.57e-1 **3.36e-2**
GPT-3.5 9.52e-2 7.25e-2
GPT-4 **2.38e-7** **6.86e-4**
GPT-4o **1.40e-4** **5.08e-5**

_Baseline_

Llama-3 70b **6.11e-4** GPT-4o **8.08e-10**

_ICL_

GPT-3.5 - 5.19e-1
GPT-4 - 1

Table 1: _p-values_ for _LiaHR_ on **SemEval** . **Reasonable-**
**ness** refers to whether human and LLM unreasonable
assessments coincide. **Preference** to whether humans
prefer model predictions over gold labels. _p-values_ are
for the hypothesis that the models agree with humans.

gap is smaller to the gold labels when compared to
SemEval. Therefore, it is evident that only a small
subset of the settings is able to _clearly_ achieve **Non-**

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

19643

QueerReclaimLex

1.0

0.8

0.6

0.4

1.0

0.8

0.6

0.4

1.0

0.8

0.6

0.4

|Col1|Col2|GPT-4o|Col4|Col5|Col6|
|---|---|---|---|---|---|
|||||||
|||Lla|ma-3-7|0b|0b|
|||||||
|||Lla|ma-2-7|0b|0b|
|||||||

|Col1|Col2|Col3|Col4|Col5|Col6|
|---|---|---|---|---|---|
|||Lla|ma-2-7|b||
|||||||

Query included with current group’s label or _opposite_ .

**conformity** and **Noise Rejection**, namely 5-shot
GPT-4o, 5-shot GPT-3.5, and 15-shot Llama-3 70b,
while these models also seem to be meeting or tending towards **Rectification** . Again, the baseline, on
the other hand, seems to be achieving consistently
lower success rates for the gold labels, but their
random performance is much lower and therefore
better at **Noise Rejection** .

**MFRC** In Appendix E, we also show our results
and very interesting findings for these three properties in MFRC, where smaller models seem to be
treating the gold and random labels similarly.

**BERT-based baseline** In Appendix L, we show
results for a BERT-based filtering baseline, showing it underperforms 5-shot GPT-4o while requiring
the entire dataset to be trained, disincentivizing its
usage from beginning to end of the data collection.

**Diversity** We examine **Diversity** separately, in
Figures 6 and 7. Figure 6 shows the success rates of
copy-pasting on MFRC and GoEmotions between
the gold, random, and individual annotator labels,
using otherwise the same exact prompts and only
differing the labels to avoid confounding factors.
We first see that all annotators tend to be clustered
together with small rejection rates, indicating that

**Micro F1**
**Setting**

**GoEmotions** **SemEval**

Original 0 _._ 652 _±_ 0 _._ 001 0 _._ 689 _±_ 0 _._ 002
Replaced **0.653** 0 _._ 000 **0.692** 0 _._ 003
_±_ _±_
Replaced (trn) 0 _._ 642 _±_ 0 _._ 001 0 _._ 680 _±_ 0 _._ 002
Filtered 0 _._ 652 _±_ 0 _._ 002 0 _._ 679 _±_ 0 _._ 002
Bsl Filtered 0 _._ 638 _±_ 0 _._ 001 0 _._ 680 _±_ 0 _._ 003
Predictions 0 _._ 427 _±_ 0 _._ 002 0 _._ 613 _±_ 0 _._ 000

Table 2: Performance of BERT-based _Demux_ on various
settings using _LiaHR_ and baseline label corrections.

the model tends to accept all different perspectives
equally. Second, we see that their performance is
better compared to random. Finally, the similarity between the annotators shown can be very low
(e.g., as low as 0.433 Jaccard Score on GoEmotions
between annotators), representing consistently different perspectives. Consequently, the _majority of_
_the disagreement between annotators is being pre-_
_served by the model_ organically, without any intervention. All these pieces of evidence indicate that
most models achieve **Diversity** . Moreover, we see
a marked difference between annotators and the aggregate, with the latter displaying higher rejection
rates, indicating that part of our aforementioned results on MFRC and GoEmotions can be explained
as aggregation artifacts (Chochlakis et al., 2025).
Figure 7 shows that _LiaHR_ can successfully accept both in-group and out-group perspectives in
the QueerReclaimLex benchmark without explicit
prompting, instead learning implicit causal cues
from few examples. Results show that the models tend to model out-group annotations better.
However, more capable models also recognize reclaimed slurs as not harmful when used by in-group
speakers, scaling performance with more demonstration, indicating the robustness of _LiaHR_ to the
guardrails placed on models, and an ability to counterbalance systematic biases with few demonstrations, a challenging problem in toxicity classifiers
with reclaimed slurs (Sap et al., 2019; Haimson
et al., 2021; Sap et al., 2022). Thus, _LiaHR_ proves
robust to our stress test for whether the model itself
might introduce biases in the dataset.

**4.4** **Human Evaluation**

Results for our human evaluations are presented
in Table 1 for SemEval for the models that meet
our defined properties. More detailed results on
**SemEval** and **GoEmotions** can be found in Ap

19644

pendix C. We see that Llama-3 70b and GPT-3.5
do not show enough discriminability between reasonable and unreasonable labels, although their
results are strong in terms of preference for their
labels when the copy-paste task was performed
incorrectly. However, GPT-4 and 4o can distinguish between reasonable and unreasonable labels
and also propose better alternatives for unreasonable labels. The results show strong statistical significance, but also large effect sizes. This is not
the case when checking for the ICL prediction of
the models. This shows that the predictions of
LLMs are not preferred over the gold labels by
humans, indicating that our settings are important
to achieve proper filtering. We also see that the
explicit baseline shows sufficient discriminability
for both Llama-3 70b and GPT-4o.

**4.5** **Ecological Validity**

In addition to the human evaluations and defining and evaluating proxy properties, we also perform ecological validity studies, and compare to
other online methods. That is, even though we
have shown the models have desirable properties,
and people tend to prefer them over the original
labels, do models trained on them perhaps show
erratic behavior? For all the settings introduced in
Section 3.3, we show the results in Table 2 (additional results in Appendix H). The results indicate
that the new labels lead to slightly better generalization performance, although the methods need
to be applied throughout the annotation process
to get the maximum benefit. Note that **SemEval**
is a smaller dataset, leading to extra performance
decreases when examples are filtered instead of
corrected. Noticeably, we also see that using the
raw predictions of the models leads to substantial
deterioration in performance. In addition to the
humans evaluations, these results indicate that our
proposal for “reasonableness” checks rather than
simply using the LLM as classifier is warranted.

**5** **Conclusion**

In this work, we propose “reasonableness” checks
to improve the signal-to-noise ratio in subjective
language annotations. We leverage LLMs and introduce _LiaHR_, which is able to both filter and correct
unreasonable annotations, and a simple baseline
that detects unreasonable annotations. We demonstrate that both approaches satisfy desirable proxy
properties, pass human evaluations, and show eco

logical validity when used to train smaller models.
Moreover, we show that the model can pick up on
causal yet implicit cues from few examples reliably.
While our experiments show that humans prefer the
model’s labels when it is performing correction, we
advocate for usage during the annotation process,
with additional checks. For example, if some submitted labels for a specific example do not pass the
_LiaHR_ filter, instead of always using its alternative
predictions, the same document can be shown to
the annotator at a later stage to verify and potentially correct the label themselves.
To further corroborate our findings on _LiaHR_,
we also show how it performs in objective tasks
in Appendix F, an analysis of the copy-paste performance across shots, model families and sizes in
Appendix G, that individual labels are uniformly
affected in Appendix I, and the robustness to the
position of the query in Appendix J.

**6** **Limitations and Ethics**

We want to emphasize that our model is not an
oracle. The model does not provide ground truth /
gold labels and could be biased in other ways.
Our work entails some potential for deliberate
misuse. Although we advocate for using individual perspectives as demonstrations in _LiaHR_
throughout our work, deliberate misuse might include skewing the perspectives in the prompt and
using the rejection from _LiaHR_ as justification for
rejecting minority labels and preventing certain
valid perspectives from entering the data (i.e., gatekeeping). Therefore, we want to emphasize that
_LiaHR_ assessments can only be considered valid
(though _not necessarily correct_ ) when the perspective being evaluated (the query label) coincides
with the perspective in the demonstrations. The
predictions of the model should not be taken into
account otherwise.
Accidental misuse includes model biases seeping into the labels. We want to note that, despite
the remarkable robustness of the framework on the
reclaim slurs dataset, **QueerReclaimLex**, its performance on the in-group data is noticeably worse
than the out-group. This indicates that there might
be some bias in the decisions of the model. Moreover, assessments of harm are inherently subjective,
reflecting differences in individual and cultural perceptions. The original work aggregates distinct
gender identities (e.g., non-binary, transgender) under the umbrella term gender-queer and treats them

19645

as largely synonymous. While this simplification
overlooks the diversity of perspectives, we follow
the original work’s adoption of this grouping as a
pragmatic choice to support our analysis. As understandings of differing perspectives continue to
evolve, future work should aim to incorporate a
broader pool of annotators and explore methods for
capturing the nuance and variability of perceived
harm across different communities. Therefore, we
urge _immense_ caution when the framework is used
in sensitive settings.
We also decreased the number of inference
queries within each seed to enable us to experiment
with many models and shots. This tradeoff means
that we do not have a high degree of confidence in
each individual result, yet the vast number of experiments demonstrating similar trends reinforces
our confidence in our general findings.
A potential confounding factor in our work is
quantization. Previous work has reported significant decreases in performance from it (Marchisio
et al., 2024). We note, first, that there is no a priori
reason for the quantization to affect our results in
a nonuniform way, e.g., affecting random labels
more than gold labels. Quantization was chosen
because of obvious computational constraints. Finally, it is plausible that even API-based models are
served quantized (e.g., mini versions). For these
reasons, we believe that quantized performance
is representative of LLM performance in realistic
scenarios. Moreover, this work does not aim to
establish the benchmark performance of LLMs in
any task, but rather to leverage their capabilities to
solve a prescient problem in subjective annotations.

**Acknowledgments**

This project was supported in part by funds from
DARPA under contract HR001121C0168, NSF
CIVIC, and USC-Capital One Center for Responsible AI Decision Making in Finance. The authors
thank Efthymios Tsaprazlis, Efthymios Georgiou,
Kleanthis Avramidis and Sabyasachee Baruah for
helpful comments.

**References**

Suhaib Abdurahman, Mohammad Atari, Farzan KarimiMalekabadi, Mona J Xue, Jackson Trager, Peter S
Park, Preni Golazizian, Ali Omrani, and Morteza Dehghani. 2024. Perils and opportunities in using large
language models in psychological research. _PNAS_
_nexus_, 3(7):pgae245.

Lora Aroyo and Chris Welty. 2015. Truth is a lie: Crowd
truth and the seven myths of human annotation. _AI_
_Magazine_, 36(1):15–24.

Brandon M Booth and Shrikanth S Narayanan. 2024.
People make mistakes: Obtaining accurate ground
truth from continuous annotations of subjective constructs. _Behavior_ _Research_ _Methods_, 56(8):8784–
8800\.

Georgios Chochlakis, Gireesh Mahajan, Sabyasachee
Baruah, Keith Burghardt, Kristina Lerman, and
Shrikanth Narayanan. 2023. Leveraging label correlations in a multi-label setting: A case study in
emotion. In _ICASSP 2023-2023 IEEE International_
_Conference on Acoustics, Speech and Signal Process-_
_ing (ICASSP)_, pages 1–5. IEEE.

Georgios Chochlakis, Alexandros Potamianos, Kristina
Lerman, and Shrikanth Narayanan. 2024. The strong
pull of prior knowledge in large language models and
its impact on emotion recognition. In _Proceedings_
_of_ _the_ _12th_ _International_ _Conference_ _on_ _Affective_
_Computing and Intelligent Interaction (ACII)_ . IEEE.

Georgios Chochlakis, Alexandros Potamianos, Kristina
Lerman, and Shrikanth Narayanan. 2025. [Aggrega-](https://doi.org/10.18653/v1/2025.naacl-long.284)
tion artifacts in [subjective](https://doi.org/10.18653/v1/2025.naacl-long.284) tasks collapse large lan[guage models’ posteriors.](https://doi.org/10.18653/v1/2025.naacl-long.284) In _Proceedings of the 2025_
_Conference of the Nations of the Americas Chapter of_
_the Association for Computational Linguistics:_ _Hu-_
_man_ _Language_ _Technologies_ _(Volume_ _1:_ _Long_ _Pa-_
_pers)_, pages 5513–5528, Albuquerque, New Mexico.
Association for Computational Linguistics.

Aida Mostafazadeh Davani, Mark Díaz, and Vinodkumar Prabhakaran. 2022. Dealing with disagreements:
Looking beyond the majority vote in subjective annotations. _Transactions of the Association for Com-_
_putational Linguistics_, 10:92–110.

Alexander Philip Dawid and Allan M Skene. 1979.
Maximum likelihood estimation of observer errorrates using the EM algorithm. _Journal of the Royal_
_Statistical_ _Society:_ _Series_ _C_ _(Applied_ _Statistics)_,
28(1):20–28.

Dorottya Demszky, Dana Movshovitz-Attias, Jeongwoo
Ko, Alan Cowen, Gaurav Nemade, and Sujith Ravi.
2020\. GoEmotions: A dataset of fine-grained emotions. In _Proceedings of the 58th Annual Meeting of_
_the Association for Computational Linguistics_, pages
4040–4054.

Jacob Devlin, Ming-Wei Chang, Kenton Lee, and
Kristina Toutanova. 2019. Bert: Pre-training of deep
bidirectional transformers for language understanding. In _Proceedings_ _of_ _the_ _2019_ _conference_ _of_ _the_
_North American chapter of the association for com-_
_putational linguistics:_ _human language technologies,_
_volume 1 (long and short papers)_, pages 4171–4186.

Rebecca Dorn, Lee Kezar, Fred Morstatter, and Kristina
Lerman. 2024. Harmful speech detection by language models exhibits gender-queer dialect bias. In
_Proceedings of the 4th ACM Conference on Equity_

19646

_and_ _Access_ _in_ _Algorithms,_ _Mechanisms,_ _and_ _Opti-_
_mization_, pages 1–12.

Anca Dumitrache, Oana Inel, Lora Aroyo, Benjamin
Timmermans, and Chris Welty. 2018. [Crowdtruth](https://arxiv.org/abs/1808.06080)
[2.0: Quality metrics for crowdsourcing with disagree-](https://arxiv.org/abs/1808.06080)
[ment.](https://arxiv.org/abs/1808.06080)

Senjuti Dutta, Sid Mittal, Sherol Chen, Deepak Ramachandran, Ravi Rajakumar, Ian Kivlichan, Sunny
Mak, Alena Butryna, and Praveen Paritosh. 2023.
Modeling subjectivity (by mimicking annotator annotation) in toxic comment identification across diverse
communities. _arXiv preprint arXiv:2311.00203_ .

Tiantian Feng and Shrikanth Narayanan. 2024. Foundation model assisted automatic speech emotion recognition: Transcribing, annotating, and augmenting.
In _ICASSP_ _2024-2024_ _IEEE_ _International_ _Confer-_
_ence_ _on_ _Acoustics,_ _Speech_ _and_ _Signal_ _Processing_
_(ICASSP)_, pages 12116–12120. IEEE.

Justin Garten, Brendan Kennedy, Joe Hoover, Kenji
Sagae, and Morteza Dehghani. 2019. Incorporating
demographic embeddings into language understanding. _Cognitive science_, 43(1):e12701.

Preni Golazizian, Ali Omrani, Alireza S Ziabari, and
Morteza Dehghani. 2024. Cost-efficient subjective
task annotation and modeling through few-shot annotator adaptation. _arXiv preprint arXiv:2402.14101_ .

Mitchell L Gordon, Michelle S Lam, Joon Sung Park,
Kayur Patel, Jeff Hancock, Tatsunori Hashimoto, and
Michael S Bernstein. 2022. Jury learning: Integrating dissenting voices into machine learning models.
In _Proceedings of the 2022 CHI Conference on Hu-_
_man Factors in Computing Systems_, pages 1–19.

Daya Guo, Dejian Yang, Haowei Zhang, Junxiao Song,
Ruoyu Zhang, Runxin Xu, Qihao Zhu, Shirong Ma,
Peiyi Wang, Xiao Bi, et al. 2025. Deepseek-r1: Incentivizing reasoning capability in llms via reinforcement learning. _arXiv preprint arXiv:2501.12948_ .

Oliver L Haimson, Daniel Delmonaco, Peipei Nie, and
Andrea Wegner. 2021. Disproportionate removals
and differing content moderation experiences for conservative, transgender, and black social media users:
Marginalization and moderation gray areas. _Proceed-_
_ings_ _of_ _the_ _ACM_ _on_ _Human-Computer_ _Interaction_,
5(CSCW2):1–35.

Jochen Hartmann, Jasper Schwenzow, and Maximilian Witte. 2023. The political ideology of conversational ai: Converging evidence on chatgpt’s
pro-environmental, left-libertarian orientation. _Left-_
_Libertarian Orientation (January 1, 2023)_ .

Dirk Hovy, Taylor Berg-Kirkpatrick, Ashish Vaswani,
and Eduard Hovy. 2013. Learning whom to trust
with MACE. In _Proceedings of the 2013 Conference_
_of_ _the_ _North_ _American_ _Chapter_ _of_ _the_ _Association_
_for_ _Computational_ _Linguistics:_ _Human_ _Language_
_Technologies_, pages 1120–1130.

Eduard Hovy, Laurie Gerber, Ulf Hermjakob, ChinYew Lin, and Deepak Ravichandran. 2001. [Toward](https://www.aclweb.org/anthology/H01-1069)
[semantics-based answer pinpointing.](https://www.aclweb.org/anthology/H01-1069) In _Proceedings_
_of the First International Conference on Human Lan-_
_guage Technology Research_ .

Alon Jacovi and Yoav Goldberg. 2020. Towards faithfully interpretable nlp systems: How should we define and evaluate faithfulness? In _Proceedings of the_
_58th Annual Meeting of the Association for Compu-_
_tational Linguistics_, pages 4198–4205.

Xin Li and Dan Roth. 2002. Learning [question](https://www.aclweb.org/anthology/C02-1150) clas[sifiers.](https://www.aclweb.org/anthology/C02-1150) In _COLING_ _2002:_ _The_ _19th_ _International_
_Conference on Computational Linguistics_ .

Alisa Liu, Zhaofeng Wu, Julian Michael, Alane Suhr,
Peter West, Alexander Koller, Swabha Swayamdipta,
Noah A Smith, and Yejin Choi. 2023. We’re afraid
language models aren’t modeling ambiguity. In _The_
_2023 Conference on Empirical Methods in Natural_
_Language Processing_ .

Kelly Marchisio, Saurabh Dash, Hongyu Chen, Dennis
Aumiller, Ahmet Üstün, Sara Hooker, and Sebastian
Ruder. 2024. How does quantization affect multilingual llms? _arXiv preprint arXiv:2407.03211_ .

Sewon Min, Xinxi Lyu, Ari Holtzman, Mikel Artetxe,
Mike Lewis, Hannaneh Hajishirzi, and Luke Zettlemoyer. 2022. Rethinking the role of demonstrations:
What makes in-context learning work? In _Proceed-_
_ings of the 2022 Conference on Empirical Methods in_
_Natural Language Processing_, pages 11048–11064.

Saif Mohammad, Felipe Bravo-Marquez, Mohammad
Salameh, and Svetlana Kiritchenko. 2018. Semeval2018 task 1: Affect in tweets. In _Proceedings of the_
_12th International Workshop on Semantic Evaluation_,
pages 1–17.

Negar Mokhberian, Frederic R Hopp, Bahareh Harandizadeh, Fred Morstatter, and Kristina Lerman. 2022.
Noise audits improve moral foundation classification. In _2022 IEEE/ACM International Conference_
_on Advances in Social Networks Analysis and Mining_
_(ASONAM)_, pages 147–154. IEEE.

Negar Mokhberian, Myrl G Marmarelis, Frederic R
Hopp, Valerio Basile, Fred Morstatter, and Kristina
Lerman. 2023. Capturing perspectives of crowdsourced annotators in subjective learning tasks. _arXiv_
_preprint arXiv:2311.09743_ .

Long Ouyang, Jeffrey Wu, Xu Jiang, Diogo Almeida,
Carroll Wainwright, Pamela Mishkin, Chong Zhang,
Sandhini Agarwal, Katarina Slama, Alex Ray, et al.
2022\. Training language models to follow instructions with human feedback. _Advances in neural in-_
_formation processing systems_, 35:27730–27744.

Susannah BF Paletz, Ewa M Golonka, Nick B Pandža,
Grace Stanton, David Ryan, Nikki Adams, C Anton Rytting, Egle E Murauskaite, Cody Buntain,
Michael A Johns, et al. 2023. Social media emotions annotation guide (SMEmo): Development and

19647

initial validity. _Behavior Research Methods_, pages
1–51.

Paul Resnick, Yuqing Kong, Grant Schoenebeck, and
Tim Weninger. 2021. Survey equivalence: A procedure for measuring classifier accuracy against human
labels. _arXiv preprint arXiv:2106.01254_ .

Maarten Sap, Dallas Card, Saadia Gabriel, Yejin Choi,
and Noah A Smith. 2019. The risk of racial bias in
hate speech detection. In _Proceedings_ _of_ _the_ _57th_
_annual meeting of the association for computational_
_linguistics_, pages 1668–1678.

Maarten Sap, Swabha Swayamdipta, Laura Vianna,
Xuhui Zhou, Yejin Choi, and Noah A. Smith. 2022.
[Annotators with Attitudes:](https://doi.org/10.18653/v1/2022.naacl-main.431) How Annotator Beliefs
And Identities Bias [Toxic](https://doi.org/10.18653/v1/2022.naacl-main.431) Language Detection. In
_Proceedings_ _of_ _the_ _2022_ _Conference_ _of_ _the_ _North_
_American Chapter of the Association for Computa-_
_tional Linguistics:_ _Human Language Technologies_,
pages 5884–5906. Association for Computational
Linguistics.

Weijia Shi, Xiaochuang Han, Mike Lewis, Yulia
Tsvetkov, Luke Zettlemoyer, and Wen-tau Yih. 2024.
Trusting your evidence: Hallucinate less with contextaware decoding. In _Proceedings of the 2024 Confer-_
_ence of the North American Chapter of the Associ-_
_ation_ _for_ _Computational_ _Linguistics:_ _Human_ _Lan-_
_guage Technologies (Volume 2:_ _Short Papers)_, pages
783–791.

Samuel Stanton, Pavel Izmailov, Polina Kirichenko,
Alexander A Alemi, and Andrew G Wilson. 2021.
Does knowledge distillation really work? _Advances_
_in Neural Information Processing Systems_, 34:6906–
6919\.

Swabha Swayamdipta, Roy Schwartz, Nicholas Lourie,
Yizhong Wang, Hannaneh Hajishirzi, Noah A Smith,
and Yejin Choi. 2020. Dataset cartography: Mapping
and diagnosing datasets with training dynamics. In
_Proceedings_ _of_ _the_ _2020_ _Conference_ _on_ _Empirical_
_Methods in Natural Language Processing (EMNLP)_,
pages 9275–9293.

Jackson Trager, Alireza S Ziabari, Aida Mostafazadeh
Davani, Preni Golazizian, Farzan KarimiMalekabadi, Ali Omrani, Zhihe Li, Brendan
Kennedy, Nils Karl Reimer, Melissa Reyes, et al.
2022\. The moral foundations reddit corpus. _arXiv_
_preprint arXiv:2208.05545_ .

Miles Turpin, Julian Michael, Ethan Perez, and Samuel
Bowman. 2024. Language models don’t always say
what they think: Unfaithful explanations in chain-ofthought prompting. _Advances in Neural Information_
_Processing Systems_, 36.

Dmitry Ustalov, Nikita Pavlichenko, and Boris Tseitlin.
2021\. Learning from crowds with crowd-kit. _arXiv_
_preprint arXiv:2109.08584_ .

Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob
Uszkoreit, Llion Jones, Aidan N Gomez, \\ Lukasz

Kaiser, and Illia Polosukhin. 2017. Attention is all
you need. _Advances in neural information processing_
_systems_, 30.

Thomas Wolf, Lysandre Debut, Victor Sanh, Julien
Chaumond, Clement Delangue, Anthony Moi, Pierric Cistac, Tim Rault, Rémi Louf, Morgan Funtowicz,
Joe Davison, Sam Shleifer, Patrick von Platen, Clara
Ma, Yacine Jernite, Julien Plu, Canwen Xu, Teven Le
Scao, Sylvain Gugger, Mariama Drame, Quentin
Lhoest, and Alexander M. Rush. 2020. [Transform-](https://www.aclweb.org/anthology/2020.emnlp-demos.6)
ers: [State-of-the-art natural language processing.](https://www.aclweb.org/anthology/2020.emnlp-demos.6) In
_Proceedings_ _of_ _the_ _2020_ _Conference_ _on_ _Empirical_
_Methods_ _in_ _Natural_ _Language_ _Processing:_ _System_
_Demonstrations_, pages 38–45, Online. Association
for Computational Linguistics.

19648

**A** **Methodology**

In this section, we present a mathematical formulation for the baseline and _LiaHR_ to avoid any potential ambiguities arising from the natural language
description of the main text. We follow the notation of Chochlakis et al. (2025). For a set of
examples _X_, and a set of labels _Y_, a dataset _D_ _[a]_

defines a mapping _f_ _[a]_ : _X_ _→Y_, where _a_ denotes
a specific annotator or the aggregate. Similarly,
_D_ _[a]_ = _{_ ( _x, y_ ) _| x ∈X_ _, y_ = _f_ _[a]_ ( _x_ ) _}_, which is characterized by joint distribution _p_ _[a]_ ( _x, y_ ). The _gold_
query pair is denoted as ( _xq, yq_ _[a]_ [)] _[,]_ _[y]_ _q_ _[a]_ [=] _[ f]_ _[a]_ [(] _[x][q]_ [)][.]

**Reasonableness Baseline** We want to sample _k_
train documents from _X_ to create a prompt with
document-label pairs, as well as corresponding binary reasonableness labels, denoted simply as 1
and 0 [6] . We choose half ( _[k]_ [) pairs to have the “rea-]

and 0 [6] . We choose half ( _[k]_ 2 [) pairs to have the “rea-]

sonable” label, and for other half the “unreasonable”
label. To sample reasonable pairs for our prompt,
we sample document-label pairs directly from _D_ _[a]_

_[r]_ _[a]_ _[k]_

as _S_ _[r]_ = ( _xi, yi,_ 1) : ( _xi, yi_ ) _p_ _[a]_ _,_ _i_ \[ _[k]_ 2
_{_ _∼_ _∈_

as _S_ _[r]_ = _{_ ( _xi, yi,_ 1) : ( _xi, yi_ ) _∼_ _p_ _[a]_ _,_ _i_ _∈_ \[ _[k]_ 2 []\] _[}]_ [.]

For unreasonable pairs, we sample the documents
_x_ and the labels _y_ independently of each other
from the dataset as _S_ _[u]_ = ( _xi, yi,_ 0) : ( _xi, yi_ )
_{_ _∼_
_p_ _[a]_ _I_ _[,]_ _[i]_ _[∈]_ \[[] _[k]_ 2 []\] _[}]_ [,] [where] _[p][a]_ _I_ [(] _[x, y]_ [)] [=] _[p][a]_ [(] _[x]_ [)] _[p][a]_ [(] _[y]_ [)][,] [in]

_p_ _[a]_ _I_ _[,]_ _[i]_ _[∈]_ \[[] _[k]_ 2 []\] _[}]_ [,] [where] _[p][a]_ _I_ [(] _[x, y]_ [)] [=] _[p][a]_ [(] _[x]_ [)] _[p][a]_ [(] _[y]_ [)][,] [in]

effect assigning random yet in-distribution labels
to each document. The complete demonstrations
for the model are _S_ = _S_ _[r]_ _∪_ _S_ _[u]_, and the order
of the examples in the prompt is determined randomly. The query document is presented with the
gold label _yd_ _[a]_ [=] _[y]_ _q_ _[a]_ [(like] _[S][r]_ [;] [“Gold] [pair”] [in] [the]
baseline figures like Figure 3) or a random label _yd_ _[a]_
independently from the query _xq_ using _p_ _[a]_ ( _y_ ) (like
_S_ _[u]_ ; “Rand pair” in the baseline figures) at the end,
and we elicit the final prediction from the model,
namely 1 or 0: _S_ _[′]_ = _S_ _∪{_ ( _xq, yd_ _[a][,]_ [ \_][)] _[}]_ [.] [We show]
the rate of 1 predictions in our results.

_**LiaHR**_ To create the prompt, we sample _k_
demonstrations for the prompt from _D_ _[a]_ with _p_ _[a]_

as _S_ = ( _xi, yi_ ) : ( _xi, yi_ ) _p_ _[a]_ _,_ _i_ \[ _k_ \] . In
_{_ _∼_ _∈_ _}_
_LiaHR_, the first demonstration is the query _xq_ . For
this demonstration, we either use its gold label
_yd_ _[a]_ [=] _[y]_ _q_ _[a]_ [(“Query] [w/] [gold”] [in] [the] _[LiaHR]_ [figures]
like Figure 2) or sample a random label _yd_ _[a]_ [inde-]
pendently from the query _xq_ using _p_ _[a]_ ( _y_ ) (“Query
w/ rand” in the _LiaHR_ figures). This query pair
is included in the prompt as the first demonstra

_**LiaHR**_ To create the prompt, we sample _k_
demonstrations for the prompt from _D_ _[a]_ with _p_ _[a]_

_[a]_

6in the actual prompt, the labels are presented as “yes” or
“no”, or “reasonable” and “unreasonable”, not as 1 and 0, as
shown in Table 3.

tion, and the query document _xq_ is appended in the
prompt, eliciting a prediction for it from the model,
_S_ _[′]_ = _{_ ( _xq, yd_ _[a]_ [)] _[} ∪]_ _[S][ ∪{]_ [(] _[x][q][,]_ [ \_][)] _[}]_ [.] [We measure and]
show the similarity between the predictions of the
model with _yd_ _[a]_ [, and only measure the similarity of]
the prediction with _yq_ _[a]_ [for “Gold perf w/ rand” in]
_LiaHR_ figures.

**B** **More Implementation Details**

We used A100 NVIDIA GPUs with 80GB VRAM
for 70B models, and A40 NVIDIA GPUs for
smaller models. The budget for OpenAI API calls
was less than $50.
For all datasets, we evaluate LLMs on the dev set.
For QueerReclaimLex, we only maintain the labels
with agreement between the two annotators. Our
splits in the dataset were random. The evaluation
set was balanced, containing 84 examples.
For the baseline, we sample the random labels for the pair similarly to the random labels
in _LiaHR_ . In the demonstrations, we use equal
amounts of pairs with gold labels and random labels. For Demux, we use the same training regime
as Chochlakis et al. (2023), using the intra loss with
a coefficient of 0 _._ 2, but training only on the train
set instead of integrating the dev set in training after early stopping. Confidence intervals are shown
from 3 model runs.
We present examples of all the prompts in Table 3. Across each dataset, the same examples are
used in the prompt within each seed when the number of shots is equal. That means that, for example,
in QueerReclaimLex, the only factor that is different across the four settings presented in Figure 7 is
the causally controlled labels reflecting in-group or
out-group perspectives.

**C** **Full Human Evaluations**

In human evaluations, to avoid biasing annotators
towards specific answers — for example, having
the dataset label always as the first option (Turpin
et al., 2024) —, we randomly interleave reasonable
and unreasonable examples (label according to the
model) for the **Reasonableness** check, whereas for
the **Preference** check, we randomly change the
order with which the label in the dataset and the
model’s prediction are presented to the annotators.
We present full results, including the number of
trials and the precise numbers of them, here in
Table 4 and Table 5. We note that we recruited
11 colleagues (6 males and 5 females, ages 20

19649

**SemEval 2018 Task 1 E-c**

Classify the following inputs into none, one, or multiple
the following emotions per input: anger, anticipation,
disgust, fear, joy, love, optimism, pessimism, sadness,
surprise and trust.

Input: ‘Skipping meals is the national way of showing
disappointment and . wiz‘
{"label": ["anger", "disgust", "sadness"]}

Input: ‘But guess what ? I’m sober‘

**GoEmotions**

Classify the following inputs into none, one, or multiple
the following emotions per input: joy, optimism, admiration, surprise, fear, sadness and anger.

Input: ‘Is this in New Orleans?? I really feel like
this is New Orleans.‘
{"label": []}

Input: ‘BANG motherfucker¡

**MFRC**

Classify the following inputs into none, one, or multiple
the following moral foundations per input: authority, care,
equality, loyalty, proportionality and purity.

Input: ‘Le Pen was absolutely terrible. That’s pretty much
all we can take out of this debate.‘
{"label": []}

Input: ‘It’s just capitalism is a pure distillation of
those bad traits‘

**QueerReclaimLex**

Consider whether the following inputs present harm or not
to the mentioned LGBTQ group, and answer with: no
harm and harm.

Input: ‘fags ew‘
Assessment: no harm

Input: ‘went from edm junkie to college dyke way
too quick‘
Assessment:

**Reasonableness baseline**

Assess the reasonableness of the provided label for each
input. Namely, evaluate whether the label makes sense
for its corresponding input, under some reasonable interpretation. Reply only with unreasonable and reasonable.

Input: ‘Skipping meals is the national way of showing
disappointment and . wiz‘
Label: surprise, optimism
Assessment: unreasonable

Input: ‘But guess what ? I’m sober‘
Label: joy
Assessment:

Table 3: Prompt template examples

28, students or researchers) to annotate to get as
many perspectives as possible and avoid biasing

|Llama-2-7b|Col2|Col3|Col4|
|---|---|---|---|
|Query w/ gold<br>Query w/rand<br>Gold perf~~w~~/ rand|Query w/ gold<br>Query w/rand<br>Gold perf~~w~~/ rand|Query w/ gold<br>Query w/rand<br>Gold perf~~w~~/ rand|Query w/ gold<br>Query w/rand<br>Gold perf~~w~~/ rand|
|Query w/ gold<br>Query w/rand<br>Gold perf~~w~~/ rand||||

Figure 9: _Baseline_ “reasonable” scores on **MFRC** when
using gold and random input-label pairs.

the result. Note that the annotators were shown

Label-in-a-Haystack success rate on MFRC

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

1.0

0.8

0.6

0.4

0.2

0.0

5 15 25 55 75
Shots

Shots

Figure 8: Success rate of copying with _LiaHR_ on
**MFRC** when using the gold and random labels for the
query in the prompt across various numbers of demonstrations. We also show performance w.r.t. the gold
labels when using random query labels.

Baseline success rate on MFRC

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

1.0

0.8

0.6

0.4

0.2

0.0

5 15 25 55 75
Shots

Shots

19650

1.00

0.75

0.50

0.25

0.00

1.00

0.75

0.50

0.25

0.00

1.00

0.75

0.50

0.25

0.00

5 15 25 55 75
Shots

Label-in-a-Haystack success rate on

SemEval 2018 Task 1

5 15 25 55 75
Shots

5 15 25 55 75
Shots

Figure 10: _Full_ scores on the copy-paste task on **SemEval** when using the gold and random labels for the query in
the prompt across various numbers of demonstrations. We also show performance w.r.t. the gold labels when using
random query labels.

the _Reasonableness baseline_ prompt from Table 3,
modified appropriately.

**D** **More models on SemEval properties**

Here, we present additional results on SemEval
with some deprecated models present in Figure 10.
We see, interestingly, that GPT-4 shows a better performance profile than GPT-4o, indicating that the
models have successfully been trained to become
more compliant to the user, even if the model disagrees, potentially decreasing the utility of _LiaHR_ .

**E** **MFRC properties**

In this section, we present the results for **Non-**
**conformity**, **Rectification**, and **Noise** **rejection**
in MFRC, in Figures 8 and 9.
We observe that even GPT-3.5 does not achieve
**Noise Rejection** and **Rectification**, but GPT-4o is
showing positive trends in the criteria we have. Interestingly, there seem to be settings were random
labels perform better than the gold ones. Here, we
hypothesize that this happens because we always
sample at least one label for the random label case,

whereas the dataset contains many examples with
no labels.

**F** **Results on objective tasks**

Here, we present some experimental results on
an objective task, the **T** ext **RE** trieval **C** onference
( **TREC** ) question classification benchmark (Li and
Roth, 2002; Hovy et al., 2001), which contains annotations for the type of information the question
pertains to, and specifically Abbreviation, Entity,
Description and abstract concept, Human being,
Location, and Numeric value. We show these results to verify the intuition that, in principle, _LiaHR_
can be used for objective tasks too. Indeed, we see
in Figure 11, the system meets our defined properties, with the **Rectification** being, in fact, very
strong in this objective setting, suggesting the models in some ways, at least implicitly, learn to represent the nuanced difference between objective and
subjective tasks.

19651

**Reasonableness** **Preference**

Correct Ratio Wrong Ratio p-value Ratio p-value

_LiaHR_
Llama-3 70b 31/14 28/17 6.57e-1 26/12 3.36e-2
GPT-3.5 27/8 29/16 9.52e-2 54/36 7.25e-2
GPT-4 25/5 4/26 2.38e-7 41/15 6.86e-4
GPT-4o 60/20 21/31 1.40e-4 49/16 5.08e-5

_baseline_
Llama-3 70b 48/12 29/31 6.11e-4 - GPT-4o 90/10 49/51 8.08e-10 -
_LiaHR_
GPT-4o 43/14 9/27 5.12e-6 36/3 3.61e-8

_baseline_
GPT-4o 57/23 33/47 2.47e-4 -

Table 4: Results of statistical ananlysis for _LiaHR_ on **SemEval** and **GoEmotions** . **Correct Ratio** refers to proportion
of dataset labels deemed reasonable vs. unreasonable by annotators when the model performed the copy-paste task
correctly, and similarly for **Wrong Ratio** when the copy-paste task was performed incorrectly. **Ratio** reflects the
times the model’s labels were preferred over the gold labels (when the model performed copy-pasting incorrectly).

**Preference**
**Model**

Ratio p-value

GPT-3.5 33/27 0.519
GPT-4 28/32 1

Table 5: Results of statistical analysis for the regular ICL
/ raw predictions setting on **SemEval** . **Ratio** reflects the
times the model’s predictions were preferred over the
gold labels.

Label-in-a-Haystack success rate on TREC

1.0

0.8

0.6

0.4

0.2

0.0

|GPT-4|Col2|
|---|---|
|Quer~~y~~ w/ gold<br>Query w/ rand<br>Gold perf w/ rand|Quer~~y~~ w/ gold<br>Query w/ rand<br>Gold perf w/ rand|
|5<br>15<br>2|5<br>55<br>75<br>Shots|

Figure 11: Scores with _LiaHR_ on **TREC** (objective
benchmark) when using the gold and random labels
for the query in the prompt across various numbers of
demonstrations. We also show performance w.r.t. the
gold labels when using random query labels.

**G** **Degradation in copy-paste**
**performance**

In this section, as a summary of our results, we
present how different model families and scale
affects the drop in copy-paste performance when
switching from the gold label for the demo query to
a random label in _Label in a Haystack_ . We demonstrate the results for SemEval in Figure 12, for GoEmotions in Figure 15, and MFRC in Figure 13. It is
interesting to look at the three model families and
observe that the more capable the model family is,
the larger the degradation in performance tends to
be. Moreover, within each family, the larger models
usually end up with worse degradation, except for
the least capable Llama-2 in some instances, where
the trend is the opposite. We therefore hypothesize
that there is a U-shaped trend, where, on the lower
end, the ability to better follow instructions leads to
smaller degradations in performance when shifting
to random labels. However, as models continue to
get larger, the pull of the priors on the posteriors
becomes greater (Chochlakis et al., 2024), leading
to greater degradation.

**H** **Extra Ecological Validity results**

For completeness, we also present the Jaccard
Score for our ecological validity studies to supplement the Micro F1 present in the main body.

19652

60%

50%

40%

30%

20%

10%

Jaccard Score degradation on SemEval 2018 Task 1

|Col1|Col2|Col3|Col4|Col5|Col6|
|---|---|---|---|---|---|
|||||||
|||||||
|||||||
|||||GPT-4<br>|GPT-4<br>|
|||||~~GPT-4~~<br>GPT-3.5<br>Llama-3-70<br>|b<br>|
|||||~~Llama-3-8b~~<br>Llama-2-70<br>Llama-2-13<br>|b<br>b<br>|
|||||~~Llama-2-7b~~||

5 15 25 55 75
Shots

Figure 12: Degradation in copy-paste performance on
**SemEval** when using random labels compared to the
dataset’s labels.

Micro F1 degradation on MFRC

25%

0%

25%

50%

75%

100%

125%

|Col1|Col2|Col3|Col4|Col5|Col6|Col7|Col8|
|---|---|---|---|---|---|---|---|
|||||||||
|||||||||
|||||||||
||||~~GPT-4o~~|~~GPT-4o~~|~~GPT-4o~~|||
||||~~GPT-4o~~|~~GPT-4o~~|~~GPT-4o~~|~~GPT-4o~~|~~GPT-4o~~|
|||||GPT-3.5<br>Llama-3-70b<br>||||
|||||~~Llama-3-8b~~<br>Llama-2-70b<br>~~Llama-2-7b~~||||
|||||||||

5 15 25 55 75
Shots

Figure 13: Degradation in copy-paste performance on
**MFRC** when using random labels compared to the
dataset’s labels.

**Jaccard Score**
**Setting**

**GoEmotions** **SemEval**

Original 0 _._ 623 0 _._ 001 **0.574** 0 _._ 001
_±_ _±_
Replaced **0.624** 0 _._ 002 **0.574** 0 _._ 003
_±_ _±_
Replaced (trn) 0 _._ 615 _±_ 0 _._ 001 0 _._ 562 _±_ 0 _._ 001
Filtered **0.624** 0 _._ 003 0 _._ 561 0 _._ 002
_±_ _±_
Bsl Filtered 0 _._ 615 _±_ 0 _._ 002 0 _._ 558 _±_ 0 _._ 002
Predictions 0 _._ 430 _±_ 0 _._ 004 0 _._ 474 _±_ 0 _._ 000

Table 6: Performance of BERT-based _Demux_ on various
settings using LLM label corrections.

Results in Table 6 show similar as in Table 2.

**I** **Filtering per Label**

We present the success rate of each individual label
for our 3 main datasets in Table 7, 8, and 9 based

on a 25-shot run with GPT-4o. We see that no label is disproportionately affected, except _trust_ in
SemEval, the label with the least amount of annotations. On GoEmotions, scores are generally lower
compared to GoEmotions, reflecting the clustering
process that has been applied to shrink the label set
to a reasonable amount.

**Emotion** **F1**

anger 0 _._ 972 0 _._ 016
_±_
anticipation 0 _._ 921 0 _._ 017
_±_
disgust 0 _._ 939 0 _._ 019
_±_
fear 0 _._ 977 0 _._ 016
_±_
joy 0 _._ 965 0 _._ 010
_±_
love 0 _._ 973 0 _._ 019
_±_
optimism 0 _._ 995 0 _._ 007
_±_
pessimism 0 _._ 922 0 _._ 034
_±_
sadness 0 _._ 994 0 _._ 008
_±_
surprise 1 _._ 000 0 _._ 000
_±_
trust 0 _._ 867 0 _._ 094
_±_

Table 7: Success rates of _LiaHR_ on SemEval using 25shot GPT-4o.

**Emotion** **F1**

admiration 0 _._ 950 0 _._ 021
_±_
anger 0 _._ 973 0 _._ 000
_±_
fear 1 _._ 000 0 _._ 000
_±_
joy 0 _._ 871 0 _._ 020
_±_
optimism 0 _._ 908 0 _._ 036
_±_
sadness 0 _._ 930 0 _._ 028
_±_
surprise 0 _._ 944 0 _._ 020
_±_

Table 8: Success rates of _LiaHR_ on GoEmotions using
25-shot GPT-4o.

**Moral foundation** **F1**

authority 0 _._ 889 0 _._ 157
_±_
care 0 _._ 939 0 _._ 043
_±_
equality 0 _._ 978 0 _._ 031
_±_
loyalty 0 _._ 974 0 _._ 036
_±_
proportionality 1 _._ 000 0 _._ 000
_±_

Table 9: Success rates of _LiaHR_ on GoEmotions using
25-shot GPT-4o.

**J** **Position of Label in the Haystack**

We also experiment with changing the position of
the query in the prompt and evaluating how all our
metrics change. We present our results in Figure 14,

19653

Label-in-a-Haystack success rate on SemEval 2018 Task 1

GPT-4o

0 3 6 9 12 15

1.0

0.5

Llama-2-70b

0.0
0 3 6 9 12 15

Llama-3-70b

0 3 6 9 12 15

Query Order in Prompt

Figure 14: Scores on the 15-shot _LiaHR_ on **SemEval** when changing the position of the query in the demonstrations.

60%

50%

40%

30%

20%

10%

0%

Jaccard Score degradation on GoEmotions

|Col1|Col2|Col3|Col4|GPT-4o<br>GPT-3.5<br>Llama-2-70b|
|---|---|---|---|---|
|||||Llama-2-7b<br>Llama-3-70b<br>|
|||||~~Llama-3-8b~~|
||||||
||||||
||||||
||||||
||||||

5 15 25 55 75
Shots

Figure 15: Degradation in copy-paste performance on
**GoEmotions** when using random labels compared to
the dataset’s labels.

with standard deviations shown. We see that no major changes are observed in the predictions of the
model, irrespective of where the query appears in
the demonstrations. It is very interesting to see
that even when the query is the last demonstration
(just before itself then), the results remain remarkably similar to when it appears first in the prompt,
separated by 15 examples with itself.

**K** **Overall Reasonableness of Annotations**

We can estimate the overall reasonableness of
the datasets by using our existing analyses. For
example, we present the derivation process for
SemEval using the GPT-4o (15-shot) _LiaHR_ results. First, looking at Figure 2, we can derive
the percentage of human annotations predicted to
be reasonable by _LiaHR_, _p_ ( _LiaHR_ reasonable) =
0 _._ 954. Then, focusing on Table 4, we can
derive the proportion of examples annotated
as unreasonable by our annotators both when
_LiaHR_ predicted reasonable and unreasonable,

The same estimate, when checking with Llama-3
70b, comes to 0 _._ 625, and with GPT-3.5 to 0 _._ 727.
The results are only an approximation, since _LiaHR_
results are presented in Jaccard Score, not accuracy.

Figure 16: Reasonableness labels: The model is instructed to perform a reasonableness check, as captured
by the label names. However, we check for the ability
of the model to correctly copy-paste the query’s label
from its prompt.

namely _p_ (reasonable _p_ (reasonable _|_ _LiaHR|_ unreasonable _LiaHR_ reasonable) = )3912= [.] Fi-4260 [,]
nally, we can estimate the overall reasonableness
of the annotations as:

_p_ (reasonable) =

_p_ (reasonable _| LiaHR_ reasonable)

_· p_ ( _LiaHR_ reasonable)

(1)

- _p_ (reasonable _| LiaHR_ unreasonable)

_·_ (1 _−_ _p_ ( _LiaHR_ reasonable))

= 0 _._ 682 _._

19654

The same procedure can be used with the baseline,
deriving more theoretically sound estimates.

**L** **BERT-based Filtering Baseline**

In this section, we present results for a BERT-based
filtering baseline, _FilterBERT_ . _FilterBERT_ ’s output is the binary decision of whether to filter a
document-label pair out of the data pool. It is a
proxy supervised baseline, as we do not use actual annotated data for reasonableness, but instead
use the same strategy as for the LLM baseline to
construct data. Namely, documents that are paired
with their gold label from the dataset are considered “reasonable” pairs. To create “unreasonable”
pairs for a document, we sample the labels from
a random document in the dataset. Practically,
we use all pairs from the original dataset, and for
each document we also create an “unreasonable”
pair, doubling the size of the dataset. The input is
formatted similarly to Demux (Chochlakis et al.,
2023), where the input consists of the CLS token,
followed by the candidate labels, in turn followed
by a SEP token, and finally the input document.
An example input, therefore, is “[CLS] anger,
anticipation, optimism [SEP] I DIDN’T ASK
FOR THIS EITHER IT JUST HAPPENED”. We use
the contextual embedding of CLS with a two-layer
neural network (again, similar to Demux) to make
the final binary prediction with a threshold of 0 _._ 5
on the output sigmoid function. Training details
are otherwise identical to Demux (note that we
have removed the intro loss coefficient because we
do not apply the classifier on each emotion of the
prompt). Our results are presented in Table 10, in
comparison to the 5-shot GPT-4o baseline results
we have already presented in Figures 3, 5 and 9.
The BERT-based model cannot be used to conduct the ecological validity tests due to the fact
that it itself needs to use the train and dev sets
to be trained, so a more direct comparison is not
possible with our current setting, a shortcoming of
using a BERT-based model for filtering. However,
from these existing results, GPT-4o seems to align
more with our intuitions of how a model should
perform. For SemEval, the performance of GPT-4o
is closer to random baseline performance compared
to BERT in rejecting emotions, and accepts more
labels. For GoEmotions, the BERT-based model
seems to learn the noise in GoEmotion arising from
the hierarchical clustering that we apply, achieving higher acceptance rates (as we have mentioned

before). The superiority of GPT-4o on MFRC is
evident.

19655

**SemEval** **GoEmotions** **MFRC**

_**FilterBERT**_
Gold pairs 0.824 _±_ 0.017 0.751 _±_ 0.010 0.181 _±_ 0.006
Rand pairs 0.244 _±_ 0.010 0.215 _±_ 0.011 0.039 _±_ 0.008

**GPT-4o (5-shot)**
Gold pairs 0.887 _±_ 0.078 0.693 _±_ 0.063 0.430 _±_ 0.254
Rand pairs 0.277 _±_ 0.235 0.243 _±_ 0.029 0.043 _±_ 0.038

Table 10: Filtering accuracy for “reasonable” vs. “unreasonable” label-document pairs using a proxy supervised
BERT-based classifier (trained on all data) and GPT-4o (5-shot). Gold pairs match the true label; Rand pairs use
randomly sampled labels.

19656
