## Prompt Stability Scoring for Text Annotation with Large Language Models

Christopher Barrie, [1] Elli Palaiologou, [2] Petter T¨ornberg [3]

1Department of Sociology, New York University
2Independent Researcher
3Institute for Logic, Language, and Computation, University of Amsterdam

February 18, 2025

**Abstract**

Researchers are increasingly using language models (LMs) for text annotation. These approaches rely only on a prompt telling the model to
return a given output according to a set of instructions. The reproducibility of LM outputs may nonetheless be vulnerable to small changes in the
prompt design. This calls into question the replicability of classification
routines. To tackle this problem, researchers have typically tested a variety of semantically similar prompts to determine what we call “prompt
stability.” These approaches remain ad-hoc and task specific. In this article, we propose a general framework for diagnosing prompt stability by
adapting traditional approaches to intra- and inter-coder reliability scoring. We call the resulting metric the Prompt Stability Score (PSS) and
provide a Python package `promptstability` for its estimation. Using six
different datasets and twelve outcomes, we classify _∼_ 3.1m rows of data
and _∼_ 300m input tokens to: a) diagnose when prompt stability is low;
and b) demonstrate the functionality of the package. We conclude by
providing best practice recommendations for applied researchers.

### **1 Introduction**

Given recent advances in natural language processing, scholars have begun de

bating whether human coders may be replaced by machine-learning tools \[Gi

lardi et al., 2023, Grossmann et al., 2023\]. Specifically, commentary has focused

on large language models (LMs), which rely on minimal researcher input and

model training for the classification of different types of data \[Ziems et al., 2024,

1

T¨ornberg, 2023a\]. Given the power of many LMs, researchers have proposed

that so-called zero-shot approaches are capable of overcoming even demanding

classification tasks [Le Mens et al., 2023, Gilardi et al., 2023]. Importantly, these

approaches represent a departure from more conventional training and testing

paradigms in supervised learning: we can now accurately classify data just by

_telling_ _a_ _model_ _what_ _we_ _want_ _it_ _to_ _do_ .

Zero- or few-shot designs require just a “prompt” to guide the model in

its classification decisions. This prompt often takes the form of a short phrase

or set of phrases indicating the desired output [T¨ornberg, 2023b]. Using these

techniques, a large number of contributions have now demonstrated that LMs

are capable of diverse classification or annotation tasks \[Gilardi et al., 2023,

T¨ornberg, 2023b, Bang et al., 2023, Qin et al., 2023, Goyal et al., 2022, Chiang

and Lee, 2023, Grossmann et al., 2023, Ziems et al., 2024\]. All of these ap

proaches rely on some minimal prompt design to classify the data in question.

We argue that the use of LMs to classify data in a zero- or few-shot setting

has analogies with the use of human coders. That is, there are comparisons

between an individual LM and an individual expert or trained human coder.

Research designs relying on content analysis of textual or other documentary

data have traditionally relied on measures of inter- or intra-coder reliability

[Lombard et al., 2002]. These are important for determining construct validity,

addressing inherent subjectivity biases involved in coding certain types of data,

and ensuring that a given design can be replicated.

Absent from recent contributions, however, is any equivalent concern with

reliability scores when using LMs \[Reiss, 2023, Ollion et al., 2023, Sclar et al.,

2023\]. This is important for several reasons. First, many researchers are now

adopting LMs as classifiers in the absence of validation data. But even if zero- or

few-shot approaches are successful with one prompt design, this does not mean

2

they will be successful with another design. Second, even when researchers do

validate by using ground-truth data, we do not know how vulnerable classifica

tions might be to small changes in the prompt design. For both of these first two

reasons, future research may therefore struggle to replicate a given approach.

Third, researchers can use our approach to determine the stability of a given

prompt design prior to validation. That is, if a given prompt is highly unstable,

the researcher has the chance to reconsider the prompt design (or target con

struct entirely) _before_ undertaking any validation steps such as manually coding

substantial amounts of data.

In this article, we outline a technique to test for what we refer to as _prompt_

_stability_ . By this we mean the consistency of model classifications between

individual runs of the _same_ prompt and individual runs of _different_ (but se

mantically similar) prompts. We do so by building an algorithm that auto

mates the generation of semantically similar prompts from a baseline prompt

provided by the user. We then feed our data to the LM and check for the

consistency of model classifications both within the same prompt and across se

mantically similar prompts. In this way, we are able to calculate an equivalent

of inter- and intra-coder reliability with LMs, which we refer to as the inter- and

intra-Prompt Stability Score (PSS). This represents an important diagnostic for

applied researchers who will be able to determine whether their chosen LM is

likely vulnerable to instability as a result of prompt design or unobserved model

features.

### **2 Coder reliability and prompt stability**

As a point of departure, it is helpful to think through the parallels between tradi

tional inter- and intra-coder reliability and prompt stability. First, we consider

the classic understanding of reliability using human coders. Here, researchers

3

ask human coders to classify (“code”) the same data once or multiple times. In

this way, we are able to tell whether the _same_ coder classifies the same data in

the same way each time (intra-coder reliability) and whether _different_ coders

classify the same data in the same way each time (inter-coder reliability). We

can summarize the advantages of using such a procedure as: objectivity, valid

ity, and replicability \[O’Connor and Joffe, 2020, Belur et al., 2021, Lamprianou,

2023\]. That is, we can be confident that classifications are not vulnerable to

subjectivity bias, that the construct being measured is likely valid, and that

the end result is replicable. For LMs, we have to reconceptualize each of these

benefits when examining prompt stability. We summarize these comparisons in

Table 1.

In Table 1 we note that when coder reliability is high, we have some (but

in no way definitive) indication that both coders and LMs are not reliant on

subjective judgment, that the construct is valid, and that the workflow is more

likely reproducible.

**Aspect** **Coder** **Reliability** **Prompt** **Stability**

Objectivity High reliability indicates
that coding decisions are not
overly reliant on subjective
judgment.

Validity High reliability suggests the
construct being measured is
valid.

Replicability High reliability means other
researchers can reproduce the
same classifications.

High stability may indicate
that biases in the model do
not significantly affect classifications.

High stability suggests the
construct being measured is
valid.

High stability means other
language models can reproduce the same classifications.

Table 1: Comparison of coder reliability and prompt stability in research contexts

These comparisons can help us think through not only the similarities be

tween human-coded and LM-coded research designs, but also the differences.

4

When we refer to intra-coder reliability, we are referring to the consistency of

one individual’s coding decisions when asked to code the same piece of data

several times. The structure of this task is analogous to asking an LM to do

the same over multiple runs. [1] This is what we refer to as the “intra-prompt

stability score (intra-PSS).”

As for inter-coder reliability, we are referring to the consistency of multi

ple individuals’ coding decisions when asked to code the same piece of data.

So what constitutes inter-coder reliability with LMs? Here, a reconceptual

ization is required. Our approach, which we refer to as the “inter-prompt

stability score (inter-PSS)”, tracks the consistency of classification outcomes

across semantically similar prompts. Comparing between different versions

of an original prompt efficiently probes the stability–and by extension likely

reproducibility—of a given design that employs LMs within its pipeline. A

further test could include taking multiple LMs (e.g., `gpt-4o,` `claude-3.5,`

`gemini-1.5,` `Llama-3.1,` `deep-seek-r1` ) and comparing coding decisions be

tween them. While we provide a routine for doing so in the Python package

and replication materials for this article, we propose intra- and inter-PSS as the

most practicable and efficient approach for testing the reliability of a particular

LM classification task.

Another question applied researchers might ask is: why do we focus on

stability rather than accuracy? Here, it is important to note that while high

stability could mean either the human/model is consistently wrong or that the

human/model is consistently producing accurate classifications, low stability is

a good indication that accuracy will also likely be low were we to repeat the

same or similar analysis. In this article, we are focusing solely on the _stability_ of

1With the caveat that an LM may exhbit variance that does not really mimic human
coders. See Barrie et al. for a higher level discussion of this. When making the comparison
between intra-coder and intra-LM reliability here, we refer to the structure of the task not
necessarily whether the two approaches are conceptually comparable.

5

outcomes, considering it a crucial step in justifying the use of a particular LM

for a classification task. We assume that applied researchers will still employ

conventional tests of the accuracy of their classifications. We are instead con

cerned with the viability and reproducibility of a given LM classification routine,

as well as its vulnerability to trivial prompt design variations. As a diagnos

tic tool and robustness test, we therefore propose using our Python package

`promptstability` .

In many applications, researchers may find that they have low inter- or

intra-coder reliability for the outcome of interest. Reasons for low reliability

scores using human coders might have to do with: ambiguous coding criteria;

complexity of the underlying data; complexity of the construct; and coder skill

or training. When transported to the context of LMs, the reasons for low

prompt stability have some crossovers. But we again have to reconceptualize

the potential underlying reasons for low prompt stability. We summarize these

in Table 2.

In summary, if prompt stability is consistently low for a given LM, this

suggests that issues related to ambiguous prompt design, data complexity, or an

ill-defined construct (the first three factors in Table 2) are at work. In contrast,

if one LM exhibits substantially lower prompt stability compared to another

LM under similar conditions, this points to differences in model capability (the

fourth factor). In what follows, we provide a routine for testing the effects

of the potential effects of the first three factors on stability within the same

LM. To evaluate the fourth factor, we conclude by outlining one routine (with

accompanying code) for comparing prompt stability both within a given LM

and across different LMs.

6

**Aspect** **Coder** **Reliability** **Prompt** **Stability**

Criteria Ambi- Ambiguous coding instrucguity tions lead to inconsistent interpretations.

Data Complex- Complex, messy, or inapity propriate data can lead to
unreliable classifications by
coders.

Outcome Com- The construct may lack a
plexity stable definition for reliable
human coding.

Skill/Capability Varying coder experience,
skill, or training may lead to
unreliable classifications.

Ambiguous prompt design
can lead to inconsistent language model outputs.

Complex, messy, or inappropriate data may result in
unreliable classifications by
the language model.

The construct may lack a
stable definition for reliable
language model classification.

Variability in language
model capability may lead
to unreliable classifications.

Table 2: Factors affecting low coder reliability and prompt stability in research
contexts

### **3 Current Approaches**

Existing work related to the reliability of LM output falls into three camps.

A first group of research examines variation in LM accuracy across different

versions of the same prompt as a method to probe LM uncertainty \[Chen and

Mueller, 2023, Shin et al., 2020, Portillo Wightman et al., 2023, Zhao et al.,

2021, Arora et al., 2022, Chen et al., 2023, Schick and Sch¨utze, 2021, Tian

et al., 2023, Feffer et al., 2024\]. The aim here is to optimize models by using the

observed stability and accuracy of outputs to improve model performance. This

is particularly necessary with more recent “closed-source” models for which we

do not have access to model weights. By utilizing the observed consistency of

prompt outputs, researchers have attempted to derive a proxy for uncertainty

[Portillo Wightman et al., 2023, Arora et al., 2022].

A second body of research focuses on providing strategies to craft better

7

prompts. Here, notable contributions include Chain-of-Thought prompting

where LMs are prompted to break down a problem into a series of reason

ing steps [Wei et al., 2022]; Generated-Knowledge prompting where the LM is

first encouraged to produce some knowledge about the problem before respond

ing to the task [Liu et al., 2021]; as well as extensions of CoT prompting such

as Tree-of-Thought [Long, 2023]. Similar to the first body of work described

above, recent contributions have attempted to iterate over these prompt designs

to select the “best” outcome according to some popularity metric \[Wang et al.,

2022, Madaan et al., 2023, Perez et al., 2021\]. For an effective survey of these

approaches see Liu et al. [2023].

In a third body of work, applied researchers have demonstrated that LMs

are capable of outperforming humans across a variety of classification and an

notation tasks \[Gilardi et al., 2023, T¨ornberg, 2023b, Bang et al., 2023, Qin

et al., 2023, Goyal et al., 2022, Chiang and Lee, 2023, Grossmann et al., 2023,

Ziems et al., 2024\]. Yet some more recent contributions have demonstrated a

notable lack of outcome stability when prompting LMs to classify social scien

tific constructs [Dentella et al., 2023, Bisbee et al., 2023]. Scholars have tried

to overcome problems of prompt instability by using e.g., “prompt perturba

tion,” and selecting the most common output from a set of semantically similar

prompts [T¨ornberg, 2023b, Ziems et al., 2024]. Others provide dedicated rou

tines for overcoming potential problems with superficial prompt formatting and

show the LMs can be extremely sensitive to features such as punctuation \[Sclar

et al., 2023\]. To date, social scientists lack any coherent approach or software to

tackle this problem, however. Against this backdrop, Ziems et al. [2024] argue

that new validation approaches are required to avoid another replication crisis

in the social sciences (see also [Bail, 2024]).

In what follows, we provide a general diagnostic approach for applied re

8

searchers. It is worth noting that the problem we aim to overcome has parallels

to previously popular approaches to the analysis of text such as topic mod

elling. Here, despite the apparent potential of topic modelling for the topical

summary of text, researchers were unaware how vulnerable their conclusions

might be to trivial variations in text preprocessing decisions. Against this back

drop, Denny and Spirling [2018] provided a general approach to assessing the

potential importance of preprocessing decisions in determining outcomes. We

argue that zero-shot learning has this vulnerability in common with unsuper

vised approaches to text analysis. We aim to provide a general solution to

diagnosing how vulnerable our conclusions are to prompt design decisions and

a best practice guide for applied researchers.

### **4 Design**

**4.1** **Data**

We use six different datasets to validate our approach and we specify two ver

sions of the outcome for each of these datasets. These are described in Table 3.

The “Analysis name” column is how we go on to refer to these data-outcome

pairs below when discussing results. The data were selected for: a) being rele

vant to social science research; b) spanning diverse types of construct; c) being

adaptable to multiple operationalizations of that construct.

The first dataset comes from Van Vliet et al. [2020] where we filter for

all content posted by United States Senators on Twitter (now X) in the two

months prior to the 2020 US Election. [2] . The second is a set of UK party

political manifestos taken from Benoit et al. [2016]. The third is a set of New

York Times news articles about a diverse range of topics taken from Young and

2This is the same data used in T¨ornberg [2023b]

9

Soroka [2012]. The fourth is a set of tweets expressing stances toward individuals

or topics in US politics Ziems et al. [2024]. [3] The fifth is a set of open-ended

survey responses from the British Election Study used in Mellon et al. [2024].

And the sixth is a series of text profiles of individual voters taken from the

American National Election Study used in Argyle et al. [2023].

3These originally derive from the SemEval-2016 dataset provided by Mohammad et al.

[2016].

10

**Dataset** **Source** **Outcomes** **Analysis** **name** **Relevant** **variation**

US Senator van Vliet et

```
          - Binary: Republican/Democrat               - Tweets (Rep. Dem.)               - Construct validity/OutTweets al. (2020)

          - Binary: Populist/Not Populist               - Tweets (Populism) come complexity
```

NYT News Young &
Articles Soroka
(2012)

- Categorical: Positive/Negative/Neutral (All Articles)

- Categorical: Positive/Negative/Neutral (Short Articles)

- News - Data complexity/Suit

- News (Short) ability

UK Mani- Benoit et al.

```
          - Binary: Left-wing/Right-wing               - Manifestos               - Construct validity/Outfestos (2016)

          - Integer: 1-10 Ideology Scale               - Manifestos Multi come complexity
```

US Politics Ziems et al.

```
          - Binary: Stance For/Against               - Stance               - Data complexity/SuitTweets (2024)

          - Categorical: For/Against/None               - Stance (Long) ability
```

BES Survey Mellon et al.

```
          - Categorical: 6 categories               - MII               - Data complexity/SuitResponses (2024)

          - Categorical: 12 categories               - MII (Long) ability
```

ANES Voter Argyle et al.

```
          - Binary: Biden/Trump (8 Variables)               - Synthetic               - Construct validity/OutProfiles (2023)

          - Binary: Biden/Trump (6 Variables)               - Synthetic (Short) come complexity
```

Table 3: Summary of datasets, outcomes, and relevant variations used in our approach.

Overall, these datasets span a broad range of outcome types (constructs)

and forms (operationalizations) relevant to social science. By including a broad

range of data, we hope to show the adaptability of our proposed software to

multiple questions.

We also designed these datasets—and their modifications—to cover the range

of reasons for potential low coder reliability described in Table 2. We modify the

data complexity or suitability in the US Senator Tweets, NYT News Articles, US

Politics Tweets, BES Survey Responses, and ANES Voter Profiles; we modify

the construct validity or outcome complexity in the US Senator Tweets, UK

Manifestos, US Politics Tweets, and BES Survey Responses. This is what we

refer to as “Relevant variation” in Table 3 and below.

For the US Senator Tweets, we prompt the LM to classify whether or not

the tweeter is Republican or Democrat and whether the tweet expresses populist

language or not. The logic of this task is to determine the stability of the LM

for a task that involves classifying short pieces of text for an outcome relevant

to the domain (tweets by Republicans or Democrats) and an outcome that is

less clearly relevant to the domain (tweets that may or may not contain Populist

language).

For the NYT articles, we prompt the LM to classify if the overall tone of

the article is positive, negative or neutral for all articles in the dataset and then

for shorter articles ( _\<_ = 1000 words) only. The logic of this second task is to

determine the stability of the LM when tasked with classifying more versus less

textual information with the expectation that coding more information into one

label will be more challenging.

For the UK Manifestos data, we prompt the LM to label the content first

as left-wing or right-wing then on ten-point ideology scale. The motivation for

this task is to determine LM stability when classifying the outcome as binary

12

or interval.

For the US Politics Tweets we filter out tweets with classification “None”

and prompt the LM to produce a binary output whereas for the second run

we retain the None category. Here, the intuition is that LM classifications may

become less stable as more in-between cases are introduced.

For the BES Survey Responses data, we prompt the LM to classify the open

ended survey responses as one of six categories that appear in the data then as

one of 12 categories that appear in the data. Here, the logic is to assess model

stability when the range of options is clearly defined versus when the range

of options contains some overlap (e.g., here: Economy-general versus Inflation

versus Living costs).

Finally, for the ANES Voter Profiles data, we take all eight variables used

in the published research when assessing the reliability of silicon election study

samples. For the first outcome, we use all eight variables including the explicitly

political variables that ask survey respondents whether they are Republican

or Democrat and their ideological outlook; for the second we omit these two

variables. The logic of this test is to determine the stability of outcomes when

omitting key information (here: variables) in the data to be classified.

The remaining two reasons for low coder reliability, of course, have to do

with the coding criteria and coder training. In an LM context, we are here

referring to the prompts we use when classifying data and the power of the LM

itself. In the next section, we describe our method for testing the stability of

prompts and prompt variants when annotating data. In the main analyses we

only use one LM but we do provide a routine and empirical test example of

cross-model comparisons in an Appendix section. Finally, it is worth noting

that for each of these datasets and outcomes, we do not use the exact prompt

design as the original article. As such, our tests are not to be understood as an

13

explicit test of the replicability of any of these published findings.

**4.2** **Method**

**4.2.1** **Intra-prompt** **stability**

For each of our datasets, we begin with an original prompt and target construct.

For example, in the case of the US politics tweets, we instruct the LM to classify

each tweet according to whether it thinks it was authored by a Democrat or

Republican Senator. For the intra-prompt stability approach, we simply take

the original prompt and classify the same _n_ rows of data 30 times. [4] For each

iteration, we then calculate a cumulative reliability score. This reliability score

is simply the overall Krippendorff’s Alpha (KA) for each iteration, which we

refer to as the intra-prompt stability score or intra-PSS. Here, we aim to mimic

a standard research design where different coders are asked to code the same

data _n_ times. In the examples below, we sample a maximum of 500 rows of

data thirty times for each dataset-outcome pairing. I.e., for each data-outcome

pairing, we classify a maximum of 15k rows of data.

Krippendorff’s Alpha is estimated using the following formula:

_α_ = 1 _−_ _[D][o]_

_De_

where _Do_ is the observed disagreement and _De_ is the expected disagreement.

For binary data, these are computed as follows:

_K_

_k_ =1

_K_

- _ock · ocl · dkl_

_l_ =1

_Do_ = [1]

_N_

_n_

_c_ =1

4It is worth noting that this doesn’t merely capture the classifications of a given model at
a given temperature, as the model can produce different probability distribution for the same
prompt when run multiple times.

14

_K_

- _ek · el · dkl_

_l_ =1

1
_De_ =
_N_ ( _N_ _−_ 1)

_K_

_k_ =1

where: _ock_ is the number of coders who assigned the value _k_ to the item

_c_ ; _ocl_ is the number of coders who assigned the value _l_ to the item _c_ ; _ek_ is

the expected number of occurrences of value _k_ ; _el_ is the expected number of

occurrences of value _l_ ; _dkl_ is the distance between values _k_ and _l_ ; _n_ is the total

number of items; _K_ is the number of unique values (categories); and _N_ is the

total number of coder assignments. [5]

For our purposes, let _D_ be the dataset with _n_ rows. For each row _i_ _∈_

_{_ 1 _,_ 2 _, . . ., n}_ and for each iteration _j_ _∈{_ 1 _,_ 2 _, . . .,_ 30 _}_, let _Ci,j_ be the classification

given by the LM. The intra-PSS for each iteration _j_ is computed as:

_PSSj_ = PSS( _C_ 1 _,j, C_ 2 _,j, . . ., Cn,j_ )

The cumulative reliability score after _k_ iterations is given by:

_PSS_ cumulative _,k_ = [1]

_k_

_k_

- _PSSj_

_j_ =1

where _k_ _∈{_ 1 _,_ 2 _, . . .,_ 30 _}_ . To calculate the confidence interval for the intra

PSS estimates at each iteration, we use a bootstrap approach detailed in full in

the Appendix.

**4.2.2** **Inter-prompt** **stability**

We then use `PEGASUS` [Zhang et al., 2019] to automate a series of semantically

similar prompts. For each generation, we increase the “temperature” of the

paraphrasing engine. The temperature in fine-tuned Transformer models like

5The formula for nominal data treats all outcomes as equally distant to each other. I.e.,
the distance between two different codings of the same data is 1 and 0 otherwise. The formula
for interval data uses the squared difference between values as a measure of distance.

15

`PEGASUS` controls how “conservative” or “creative” the model is. In effect, these

parameters are increasing or decreasing acceptable variance in models logits

under the hood. By increasing the temperature, we are effectively widening the

acceptable variance in the logits of the next token.

We use this feature of generative models to produce a series of increasingly

semantically dissimilar prompts. The intuition here is that a higher tempera

ture will produce prompts that are more semantically distant from the original

prompt. It is important to note that at higher temperatures, the paraphrased

prompts may contain garbled or inaccurate prompts. This is precisely the ob

jective of using this technique. If these incoherent prompts produce unstable

outcomes, the researcher can inspect why and conclude that the low quality

prompt is at fault. If the prompt produces unstable outcomes even at low tem

peratures when the prompt remains coherent, then this is an indication that

the design is fragile. We detail our recommendations to applied researchers in

a subsequent section.

We then iterate through different versions of the prompt for each tempera

ture and classify the data _n_ times across each prompt. For each temperature, we

are then able to plot the inter-prompt stability scores (inter-PSS). We use the

same bootstrapping approach as before with one difference: here, we estimate

the bootstrapped confidence intervals within each individual temperature. We

expect that as the prompt becomes more semantically distant from the original,

the variance in the prompt stability scores will also increase given the decrease

in description precision of coding guidelines (prompts). In the examples below,

we generate ten prompt variations for each temperature. For each data-outcome

pairing, we randomly sample a maximum of 500 rows for classification and we

iterate across twenty-five temperatures from 0.1 to 5.0. In sum, for each dataset,

we code a maximum of 5000 rows for each temperature and for each prompt

16

variation we annotate the same for 3 iterations (i.e., 10 variations _×_ max. 500

rows of data _×_ 3 iterations) for twenty-five temperatures (i.e., a maximum of

15000 _×_ 25 = 375000).

Formally, let _D_ be the dataset with _n_ rows. For each prompt variation

_pv_ (with _pv_ _∈{_ 11 _,_ 12 _, . . .,_ 110 _,_ 21 _,_ 22 _, . . ., P_ 10 _}_, where _P_ denotes the number

of temperature groups, each with 10 variations), for each temperature _j_ _∈_

_{_ 1 _,_ 2 _, . . .,_ 25 _}_, and for each iteration _t ∈{_ 1 _,_ 2 _,_ 3 _}_, let

_Ci,j,t_ [(] _[p][v]_ [)]

be the classification given by the LM for row _i_ at temperature _j_ using prompt

variation _pv_ on iteration _t_ .

The inter-prompt stability score (inter-PSS) for each prompt variation _pv_

and temperature _j_ is computed as:

_PSSj_ [(] _[p][v]_ [)] = _T_ [1]

_T_

- PSS� _C_ 1 [(] _[p]_ _,j,t_ _[v]_ [)] _[,]_ _[C]_ 2 [(] _[p]_ _,j,t_ _[v]_ [)] _[,]_ _[. . .,]_ _[C]_ _n,j,t_ [(] _[p][v]_ [)] - _,_

_t_ =1

where _T_ = 3 is the number of iterations.

The overall stability score for prompt variation _pv_ after _k_ temperatures is

given by:

_PSS_ avg [(] _[p][v]_ _,k_ [)] [=] [1]

_k_

_k_

- _PSSj_ [(] _[p][v]_ [)] _,_

_j_ =1

where _k_ _∈{_ 1 _,_ 2 _, . . .,_ 25 _}_ . Within each temperature, we estimate _PSSj_ [(] _[p][v]_ [)]

across the multiple temperature settings and then average the _PSS_ within each

temperature. This is repeated for each prompt variation within each temper

ature to estimate the final inter-PSS. To calculate the confidence interval for

inter-PSS within each individual prompt variation _pv_, we again use a bootstrap

approach detailed in full in the Appendix.

17

A full list of the original prompts and prompt variants that we test is pro

vided in the anonymous Github for this article. [6] Note that, for each prompt,

we also specify a `prompt` `postfix`, which specifies the type of output the model

should provide (e.g., binary, interval). This remains constant across all vari

ations of the prompts we use for the inter-prompt stability estimates. The

rationale for this is simple: we are interested in the consistency of results across

variations in target construct descriptions(i.e., prompts)—not in the format of

the output. By fixing the format of the output, we aim to isolate variation in

classification stability that results from semantic variation in the prompt and

not stochastic differences in output formatting.

For some iterations of the intra-PSS examples and some temperatures of the

inter-PSS examples, the model fails to return the desired output format. This

is a known problem (see e.g., Mellon et al. [2024]). We therefore to choose to

filter (reformat) the data in two ways. First: we filter out annotations that do

not match the desired integer format specified in the `prompt` ~~`p`~~ `ostfix` . This

might, however, mean that for some intra-PSS iterations and some inter-PSS

temperatures that we have significantly fewer annotations over which we are

calculating the scores. As such, we also estimate our scores on data that is

filtered and balanced to include in each iteration/temperature only the number

of rows equal to the minimum number across all iterations/temperatures for

that dataset after filtering. We refer to these as the ”Filtered” and ”Filtered

and balanced” data in turn.

In the main results below, we use GPT-3.5 ( `gpt-3.5-turbo` ) from OpenAI.

We also provide results for poor performing tests using an updated OpenAI

model ( `gpt-4o` ). Importantly, our software package is LM agnostic meaning

it is operable across multiple LMs. In the main software package, we include

examples of how to implement the main functions using a range of open-source

6See: `[https://anonymous.4open.science/r/promptstability-7AD3](https://anonymous.4open.science/r/promptstability-7AD3)` .

18

models. In the Appendix we also provide an example of comparing between

models by comparing between `gpt-4o` and `DeepSeek-r1` .

### **5 Results**

We visualize the results of our tests in Figures 1 and 2. [7] In Appendix Figure

B.2, we provide information on the number of unique annotations across each

iteration. A high number of unique annotations indicates that the model has

failed to return annotations in the constrained format specified by our prompt.

Only the MII dataset suffered from this problem.

We see that, for the intra-prompt stability approach, we see relatively stable

outputs across all datasets. For most, the averaged intra-PSS is above 0.8 across

all runs. This is largely as expected. Remember that here we are using prompts

that are close to the original prompts used in the published researcher where

these routines were shown to be successful. According to our results, it is clear,

first, that practitioners need to pay attention to the format of the LM response.

For example, when estimating the intra-PSS on the original annotations, both

MII and MII (long) scores are _relatively_ a lot lower than their scores when

estimating on the filtered data. Second, it is clear that when the annotation

task is particularly challenging—as is the case with the shortened Synthetic

data—the intra-PSS scores are among the least consistent.

As for the inter-prompt stability approach, we see in Figure 2 first that the

stability of outputs generally decreases as temperature increases. This is as

expected: as the prompt becomes more semantically distant from the original,

we expect the stability of classifications to reduce as a result of the degradation

in quality of coding guidelines (prompts). In Appendix Figure B.4, we display

7We provide the original intra-PSS scores with bootstrapped standard errors in Appendix
Figure B.1

19

Figure 1: Combined intra-prompt stability scores ordered by average score.

the number of unique annotations by temperature. Generally speaking, the

number of unique annotations increases as temperature increases, indicating

that the model is more likely to fail to return properly formatted annotations

as the prompt quality degrades.

Some common patterns emerge. Those datasets where we see the least

(most) stable PSS across temperatures are the datasets where either the data

are (well-) ill-suited or the outcome construct is (precisely) imprecisely defined.

To take the Synthetic (short) data as an example, we see that for this challeng

ing task where the data are not well suited to the annotation task, intra-PSS

decreases quickly. We also see once again the importance of filtering the data.

From the Original data, it might appear that LM performance for the MII

tasks decreases quickly at low temperatures. However, this is because the LM

20

Figure 2: Combined inter-prompt stability scores, ordered by average score.

returned annotations in natural language (e.g., “This text is about the environ

ment” instead of the integer coding “40”).

Finally, it is particularly notable that for some of the data-outcome pairings,

we see that PSS rapidly decreases even at low temperatures. This is the case

with all of the data-outcome pairings in the bottom row of Figure 2. We go on

to anticipate and answer several questions that applied researchers may have

when implementing the approach described above.

**5.1** **How** **much** **does** **this** **all** **cost?**

Applied researchers may reasonably object to the approach we outline above

that it may be prohibitively expensive. Commercial LM APIs price API calls

per 1m input and output tokens (words). In our empirical tests, we make many

21

tens of thousands of API calls. But how many would an applied researcher need

to make?

To answer this question, we re-estimate the inter-PSS for each dataset but

iterate through smaller to larger random subsamples of the (filtered) data. The

smallest percentage sample is 2% and the largest 75%. We see from Figure 3

that even for 2% of the sample, we are able to recover the basic trends for most

datasets.

Figure 3: Combined inter-prompt stability scores for random subsamples.

In Tables 4 and 5 we calculate the total cost for the analyses we conducted as

well as how much they would cost if we reduced the annotation sample size. We

see that even for the sizeable number of iterations, temperatures, and variations

that we conducted, the cost (here for using `gpt-3.5-turbo` is minimal. A

researcher could adequately redo these analyses with for a cost ranging from 3

22

to 150 USD depending on the sample size they used. Finally, we estimate what

the costs would have been had we conducted these tests (for the full sample size)

with a range of other open- and closed-source LM alternatives. We provide these

in Appendix Table C.1.

23

Dataset TotalRows Input tokens total Output tokens total Avg. tokens/call

Manifestos 276347 25968922 276347 94
Manifestos Multi 276201 25954819 276201 94
MII 251378 458994 251378 2
MII (Long) 233670 462566 233670 2
News 409734 198099296 409734 483
News (Short) 84451 10257657 84451 121
Stance 412362 6881473 412362 17
Stance (Long) 264775 4459825 264775 17
Synthetic 395563 16240554 395563 41
Synthetic (Short) 374733 11604411 374733 31
Tweets (Populism) 82405 3001132 82405 36
Tweets (Rep. Dem.) 82403 3001306 82403 36
Total 3144022 306390955 3144022

Table 4: Total size and tokens by dataset

Dataset Input cost Output cost Total cost 2% 5% 10% 25% 50% 75%

Manifestos 12.98 0.41 13.40 5527 13817 27635 69087 138174 207260
Manifestos Multi 12.98 0.41 13.39 5524 13810 27620 69050 138100 207151
MII 0.23 0.38 0.61 5028 12569 25138 62844 125689 188534
MII (Long) 0.23 0.35 0.58 4673 11684 23367 58418 116835 175252
News 99.05 0.61 99.66 8195 20487 40973 102434 204867 307300
News (Short) 5.13 0.13 5.26 1689 4223 8445 21113 42226 63338
Stance 3.44 0.62 4.06 8247 20618 41236 103090 206181 309272
Stance (Long) 2.23 0.40 2.63 5296 13239 26478 66194 132388 198581
Synthetic 8.12 0.59 8.71 7911 19778 39556 98891 197782 296672
Synthetic (Short) 5.80 0.56 6.36 7495 18737 37473 93683 187366 281050
Tweets (Populism) 1.50 0.12 1.62 1648 4120 8240 20601 41202 61804
Tweets (Rep. Dem.) 1.50 0.12 1.62 1648 4120 8240 20601 41202 61802
Total 153.20 4.72 157.91 3.16 7.90 15.79 39.48 78.96 118.43

Table 5: Cost estimates for each dataset by percentile

**5.2** **Are** **the** **generated** **prompts** **actually** **reliable?**

In the approach described above, we automate prompt generation with a machine

learning paraphraser tool across multiple temperatures. We use this technique

as we expect that, as we increase the temperature, the prompt will become

more semantically distant from the original and less stable. This is informa

tive because the researcher can then observe at what point the classification

procedure breaks down. This therefore provides a useful diagnostic for under

standing when and why the omission or inclusion of certain information in a

prompt reduces stability.

One objection to this approach is that we don’t have the ability to control

the prompt generation ourselves as researchers. To this, we have two responses.

First, taking away control of the generation of prompts also has advantages. A

well-known problem in ostensibly unsupervised machine-learning methods is the

tendency of researchers to re-tune parameters until they results conform with

their priors [Chang et al., 2009, Grimmer and Stewart, 2013]. By automat

ing the generation of prompts, we reduce these researcher degrees of freedom

and discourage practitioners from selecting only variations of well-performing

prompts that give a false picture of prompt stability. Second, we do include

in the package functionality the option to edit prompts when the automated

prompts are not appropriate for the task at hand. We nonetheless caution

researchers that, when editing prompts, they should: a) have good reason to

do so (e.g., automation not working as prompt too long or breaking down at

low temperatures because of early omissions of one crucial word); b) be fully

transparent in the edits that have taken place; c) provide full code necessary to

reproduce the prompt stability analysis undertaken.

A second objection is that the prompts generated are in some other way

faulty, meaning that it is the proposed routine that is at fault for giving a

26

faulty impression of instability. That is, if the prompts are just bad prompts

(especially at low temperatures), then it should be unsurprising that stability

is low. In response to this, we provide in our replication materials a routine to

inspect poor performing prompts (defined as returning a PSS _\<_ .8) as well as

a file containing all of these prompts and the score they returned. Inspecting

these prompts, it is clear that for many the original meaning of the prompt is

retained.

Finally, it is worth noting how to interpret poor performing prompts where

the meaning is garbled. This is not in and of itself a _problem_ for our approach.

Indeed, as we outline below, we should be particularly worried when the PSS

decreases at low temperatures for relatively coherent prompts. If it decreases

in response to a garbled prompt, the researcher can reasonably attribute this to

the prompt quality.

**5.3** **Are** **other** **LMs** **more** **stable?**

In our main analyses, we find that—for some datasets—the inter-PSS decreases

even at low temperatures. One might expect that the latest commercial LMs

would perform better than the LM we use ( `gpt-3.5-turbo` ), which has since

been surpassed by newer models. To test this conjecture, we take the four worst

performing dataset and outcome pairings (News (Short); News; Stance (Long);

and Synthetic (Short) and re-estimate the inter-PSS using `gpt-40-min` . We see

in Figure 4 that while this model produces annotations that are indeed more

stable, the Synthetic (Short) data is about as stable as in the main analyses.

**5.4** **What** **constitutes** **acceptable** **stability?**

In our study, we refrain from recommending a specific cutoff or acceptable

threshold for overall prompt stability. The commonly accepted metric of 0.8

27

Figure 4: Combined inter-prompt stability scores for lowest inter-PSS outcomes
in main analyses.

is frequently used to signify “very good” agreement in the calculation of Krip

pendorff’s Alpha (though see Krippendorff [2004]). We suggest that if a prompt

does not achieve an intra-prompt PSS above 0.8 after the initial run, the re

searcher should investigate the underlying causes of this variance. For inter-PSS,

we advise that if the score falls below 0.8 at a particular temperature (and es

pecially at low temperatures), the researcher should scrutinize the prompt vari

ant to determine its semantic validity, ensuring it retains the same substantive

meaning as the original prompt. If it does have the same substantive meaning

and still breaks down, this is strong indication that the routine is unstable and

therefore less likely to replicate with e.g., a different LM or adapted prompt

design in future research.

**5.5** **What** **about** **inter-model** **stability?**

When conceptualizing the similarities and differences between inter-coder and

inter-LM stability, we noted that another reason for low stability may be vari

ability in language model capability. Applied researchers may also be interested

in whether other, open-weight, models constitute a viable alternative to their

selected model. In the replication materials for this article, we include an intra

28

and inter-PSS annotation routine using one of the latest DeepSeek \[DeepSeek-AI

et al., 2025\] models and demonstrate how to run this locally using `ollama` . We

choose these models as they are the most performant closed-source and open

weights models currently available. [8] We display the results for the Manifestos

dataset in Figure 5. We see that the intra-PSS is relatively stable but lower

than for `gpt-4o` and that the performance of `deepseek-r1:8b` degrades a lot

faster as temperature increases for the inter-PSS routine.

Figure 5: Combined intra- and inter-prompt stability scores for DeepSeek-R1
and GPT-4o.

**5.6** **Parameter** **stability**

We also know that LMs may be more less vulnerable to output variations based

on the tuning of key model parameters. The most important of these are the

`temperature` setting of the model and the `top` ~~`p`~~ setting. Both of these param

eters have an influence on how conservative the model is when producing its

output. [9] As a result, researchers should also be aware that the stability and

8Note: we are here using the smallest open-weights DeepSeek-R1 model as larger moders
require more compute than most researchers will have at their disposal to run locally in a
reasonable amount of time
9For models like OpenAI’s GPT-3.5 and GPT-4, the user can also adapt the “Frequency
penalty” and “Presence penalty.” Both of these control, in different ways, the creativity of the
model by preventing it from using the same phrases or producing the same topics respectively.
For classification tasks, it is less common for users to adapt these. For this reason, and for
reasons of parsimony, we hold these parameters constant. A low temperature is generally
recommended for text annotation. In our examples we hold it constant at .1. We also keep
`top` ~~`p`~~ at its default setting of 1.

29

accuracy of their outcomes may depend on these parameters. We leave the task

of determining the stability of outcomes when iterating over these additional

parameters to future research.

### **6 Conclusion**

In this article, we have set out a self-contained approach for testing the stability

of a given prompt design when using LMs in social science research. We include

in our dedicate `promptstability` Python package a set of functions that can

reproduce all of the analyses described above. Scratch code for this functionality

is listed in Appendix listings 1 and 2. This is important because the few existing

approaches to cognate problems remain ad-hoc and task specific. Our approach,

by contrast, is generalizable, open-source, and adaptable to diverse applications

in the social sciences (and beyond). This approach will be valuable for two main

reasons: 1) for determining the likely reproducibility of a given approach that

relies on LMs; 2) for determining whether or not a given prompt design is even

feasible given the target construct _prior_ to undertaking laborious validation

steps.

To achieve this, we classified _>_ 150k rows of data across six datasets and

twelve different outcomes. This allowed us not only to test the performance of

the software package we developed but also to begin to diagnose when prompt

stability tends to be low. We find that when data is inappropriate for the task

at hand or when the target construct is under-specified, prompt stability tends

to be low.

Of course, there remain important avenues for future research. Our approach

does not adapt or iterate through other important model parameters such as

the temperature of the actual classification engine or `top` `p` settings. We also

do not compare the performance of different LMs—though our software pack

30

age is inter-operable across multiple LMs, requiring only two parameters in a

basic annotation function. Finally, we only utilize one paraphrasing engine.

Future applications may consider either alternative paraphrasing approaches or

leveraging the power of other LMs to automate the prompt variants.

### **7 Data Availability Statement**

All code and data used for the above analyses can be found at the anonymized

Github repo: `[https://anonymous.4open.science/r/promptstability-7AD3](https://anonymous.4open.science/r/promptstability-7AD3)` .

The Python package can be accessed at: `[https://pypi.org/project/promptstability/](https://pypi.org/project/promptstability/)` .

31

### **References**

Fabrizio Gilardi, Meysam Alizadeh, and Ma¨el Kubli. Chatgpt outperforms

crowd workers for text-annotation tasks. _Proceedings of the National Academy_

_of_ _Sciences_, 120(30):e2305016120, 2023.

Igor Grossmann, Matthew Feinberg, Dawn C. Parker, Nicholas A. Chris

takis, Philip E. Tetlock, and William A. Cunningham. Ai and the trans

formation of social science research. _Science_, 380(6650):1108–1109, 2023.

doi: 10.1126/science.adi1778. URL `[https://www.science.org/doi/abs/](https://www.science.org/doi/abs/10.1126/science.adi1778)`

`[10.1126/science.adi1778](https://www.science.org/doi/abs/10.1126/science.adi1778)` .

Caleb Ziems, William Held, Omar Shaikh, Jiaao Chen, Zhehao Zhang, and Diyi

Yang. Can large language models transform computational social science?

_Computational_ _Linguistics_, 50(1):237–291, 2024.

Petter T¨ornberg. How to use llms for text analysis. _arXiv_ _preprint_

_arXiv:2307.13106_, 2023a.

Ga¨el Le Mens, Bal´azs Kov´acs, Michael T Hannan, and Guillem Pros. Uncovering

the semantics of concepts using gpt-4. _Proceedings_ _of_ _the_ _National_ _Academy_

_of_ _Sciences_, 120(49):e2309350120, 2023.

Petter T¨ornberg. Chatgpt-4 outperforms experts and crowd workers in an

notating political twitter messages with zero-shot learning. _arXiv_ _preprint_

_arXiv:2304.06588_, 2023b.

Yejin Bang, Samuel Cahyawijaya, Nayeon Lee, Wenliang Dai, Dan Su, Bryan

Wilie, Holy Lovenia, Ziwei Ji, Tiezheng Yu, Willy Chung, et al. A multitask,

multilingual, multimodal evaluation of chatgpt on reasoning, hallucination,

and interactivity. _arXiv_ _preprint_ _arXiv:2302.04023_, 2023.

32

Chengwei Qin, Aston Zhang, Zhuosheng Zhang, Jiaao Chen, Michihiro Ya

sunaga, and Diyi Yang. Is chatgpt a general-purpose natural language pro

cessing task solver? _arXiv_ _preprint_ _arXiv:2302.06476_, 2023.

Tanya Goyal, Junyi Jessy Li, and Greg Durrett. News summarization and

evaluation in the era of gpt-3. _arXiv_ _preprint_ _arXiv:2209.12356_, 2022.

Cheng-Han Chiang and Hung-yi Lee. Can large language models be an alter

native to human evaluations? _arXiv_ _preprint_ _arXiv:2305.01937_, 2023.

Matthew Lombard, Jennifer Snyder-Duch, and Cheryl Campanella Bracken.

Content analysis in mass communication: Assessment and reporting of inter

coder reliability. _Human_ _communication_ _research_, 28(4):587–604, 2002.

Michael V. Reiss. Testing the reliability of chatgpt for text annotation and

classification: A cautionary remark, 2023.

Etienne Ollion, Rubing Shen, Ana Macanovic, and Arnault Chatelain. Chatgpt

for text annotation? mind the hype!, October 2023. URL `[http://dx.doi.](http://dx.doi.org/10.31235/osf.io/x58kn)`

`[org/10.31235/osf.io/x58kn](http://dx.doi.org/10.31235/osf.io/x58kn)` .

Melanie Sclar, Yejin Choi, Yulia Tsvetkov, and Alane Suhr. Quantify

ing language models’ sensitivity to spurious features in prompt design or:

How i learned to start worrying about prompt formatting. _arXiv_ _preprint_

_arXiv:2310.11324_, 2023.

Cliodhna O’Connor and Helene Joffe. Intercoder reliability in qualitative re

search: debates and practical guidelines. _International_ _journal_ _of_ _qualitative_

_methods_, 19:1609406919899220, 2020.

Jyoti Belur, Lisa Tompson, Amy Thornton, and Miranda Simon. Interrater

reliability in systematic review methodology: exploring variation in coder

decision-making. _Sociological_ _methods_ _&_ _research_, 50(2):837–865, 2021.

33

Iasonas Lamprianou. Measuring and visualizing coders’ reliability: New ap

proaches and guidelines from experimental data. _Sociological_ _Methods_ _&_ _Re-_

_search_, 52(1):525–553, 2023.

Christopher Barrie, Alexis Palmer, and Arthur Spirling. Replication for lan

guage models problems, principles, and best practice for political science.

Jiuhai Chen and Jonas Mueller. Quantifying Uncertainty in Answers from any

Language Model and Enhancing their Trustworthiness, October 2023. URL

`[http://arxiv.org/abs/2308.16175](http://arxiv.org/abs/2308.16175)` . arXiv:2308.16175 [cs].

Taylor Shin, Yasaman Razeghi, Robert L. Logan IV, Eric Wallace, and Sameer

Singh. AutoPrompt: Eliciting Knowledge from Language Models with Au

tomatically Generated Prompts, November 2020. URL `[http://arxiv.org/](http://arxiv.org/abs/2010.15980)`

`[abs/2010.15980](http://arxiv.org/abs/2010.15980)` . arXiv:2010.15980 [cs].

Gwenyth Portillo Wightman, Alexandra Delucia, and Mark Dredze. Strength

in Numbers: Estimating Confidence of Large Language Models by Prompt

Agreement. In _Proceedings_ _of_ _the_ _3rd_ _Workshop_ _on_ _Trustworthy_ _Natural_ _Lan-_

_guage_ _Processing_ _(TrustNLP_ _2023)_, pages 326–362, Toronto, Canada, 2023.

Association for Computational Linguistics. doi: 10.18653/v1/2023.trustnlp-1.

28. URL `[https://aclanthology.org/2023.trustnlp-1.28](https://aclanthology.org/2023.trustnlp-1.28)` .

Tony Z. Zhao, Eric Wallace, Shi Feng, Dan Klein, and Sameer Singh. Cal

ibrate Before Use: Improving Few-Shot Performance of Language Models,

June 2021. URL `[http://arxiv.org/abs/2102.09690](http://arxiv.org/abs/2102.09690)` . arXiv:2102.09690 [cs].

Simran Arora, Avanika Narayan, Mayee F. Chen, Laurel Orr, Neel Guha, Kush

Bhatia, Ines Chami, Frederic Sala, and Christopher R´e. Ask Me Anything:

A simple strategy for prompting language models, November 2022. URL

`[http://arxiv.org/abs/2210.02441](http://arxiv.org/abs/2210.02441)` . arXiv:2210.02441 [cs].

34

Yanda Chen, Chen Zhao, Zhou Yu, Kathleen McKeown, and He He. On the

Relation between Sensitivity and Accuracy in In-context Learning, February

2023. URL `[http://arxiv.org/abs/2209.07661](http://arxiv.org/abs/2209.07661)` . arXiv:2209.07661 [cs].

Timo Schick and Hinrich Sch¨utze. Exploiting Cloze Questions for Few Shot

Text Classification and Natural Language Inference, January 2021. URL

`[http://arxiv.org/abs/2001.07676](http://arxiv.org/abs/2001.07676)` . arXiv:2001.07676 [cs].

Katherine Tian, Eric Mitchell, Allan Zhou, Archit Sharma, Rafael Rafailov,

Huaxiu Yao, Chelsea Finn, and Christopher D. Manning. Just Ask for Cal

ibration: Strategies for Eliciting Calibrated Confidence Scores from Lan

guage Models Fine-Tuned with Human Feedback, October 2023. URL

`[http://arxiv.org/abs/2305.14975](http://arxiv.org/abs/2305.14975)` . arXiv:2305.14975 [cs].

Michael Feffer, Ronald Xu, Yuekai Sun, and Mikhail Yurochkin. Prompt explo

ration with prompt regression. _arXiv_ _preprint_ _arXiv:2405.11083_, 2024.

Jason Wei, Xuezhi Wang, Dale Schuurmans, Maarten Bosma, Fei Xia, Ed Chi,

Quoc V Le, Denny Zhou, et al. Chain-of-thought prompting elicits reason

ing in large language models. _Advances_ _in_ _Neural_ _Information_ _Processing_

_Systems_, 35:24824–24837, 2022.

Jiacheng Liu, Alisa Liu, Ximing Lu, Sean Welleck, Peter West, Ronan Le Bras,

Yejin Choi, and Hannaneh Hajishirzi. Generated knowledge prompting for

commonsense reasoning. _arXiv_ _preprint_ _arXiv:2110.08387_, 2021.

Jieyi Long. Large language model guided tree-of-thought. _arXiv_ _preprint_

_arXiv:2305.08291_, 2023.

Xuezhi Wang, Jason Wei, Dale Schuurmans, Quoc Le, Ed Chi, Sharan Narang,

Aakanksha Chowdhery, and Denny Zhou. Self-consistency improves chain

35

of thought reasoning in language models. _arXiv_ _preprint_ _arXiv:2203.11171_,

2022.

Aman Madaan, Niket Tandon, Prakhar Gupta, Skyler Hallinan, Luyu Gao,

Sarah Wiegreffe, Uri Alon, Nouha Dziri, Shrimai Prabhumoye, Yiming Yang,

et al. Self-refine: Iterative refinement with self-feedback. _arXiv_ _preprint_

_arXiv:2303.17651_, 2023.

Ethan Perez, Douwe Kiela, and Kyunghyun Cho. True few-shot learning with

language models. _Advances_ _in_ _neural_ _information_ _processing_ _systems_, 34:

11054–11070, 2021.

Pengfei Liu, Weizhe Yuan, Jinlan Fu, Zhengbao Jiang, Hiroaki Hayashi, and

Graham Neubig. Pre-train, prompt, and predict: A systematic survey of

prompting methods in natural language processing. _ACM Computing Surveys_,

55(9):1–35, 2023.

Vittoria Dentella, Fritz G¨unther, and Evelina Leivada. Systematic testing of

three language models reveals low language accuracy, absence of response

stability, and a yes-response bias. _Proceedings_ _of_ _the_ _National_ _Academy_ _of_

_Sciences_, 120(51):e2309583120, 2023.

James Bisbee, Joshua Clinton, Cassy Dorff, Brenton Kenkel, and Jennifer Lar

son. Artificially precise extremism: how internet-trained llms exaggerate

our differences. _SocArXiv_ _Preprint_, 2023. doi: 10.31235/osf.io/5ecfa. URL

`[https://doi.org/10.31235/osf.io/5ecfa](https://doi.org/10.31235/osf.io/5ecfa)` .

Christopher A Bail. Can generative ai improve social science? _Proceedings_ _of_

_the_ _National_ _Academy_ _of_ _Sciences_, 121(21):e2314021121, 2024.

Matthew J Denny and Arthur Spirling. Text preprocessing for unsupervised

36

learning: Why it matters, when it misleads, and what to do about it. _Political_

_Analysis_, 26(2):168–189, 2018.

Livia Van Vliet, Petter T¨ornberg, and Justus Uitermark. The twitter parlia

mentarian database: Analyzing twitter politics across 26 countries. _PLoS one_,

15(9):e0237073, 2020.

Kenneth Benoit, Drew Conway, Benjamin E Lauderdale, Michael Laver, and

Slava Mikhaylov. Crowd-sourced text analysis: Reproducible and agile pro

duction of political data. _American_ _Political_ _Science_ _Review_, 110(2):278–295,

2016.

Lori Young and Stuart Soroka. Affective news: The automated coding of senti

ment in political texts. _Political_ _communication_, 29(2):205–231, 2012.

Saif Mohammad, Svetlana Kiritchenko, Parinaz Sobhani, Xiaodan Zhu, and

Colin Cherry. Semeval-2016 task 6: Detecting stance in tweets. In _Proceedings_

_of_ _the_ _10th_ _International_ _Workshop_ _on_ _Semantic_ _Evaluation_ _(SemEval-2016)_,

pages 31–41, San Diego, California, 2016. Association for Computational Lin

guistics.

Jonathan Mellon, Jack Bailey, Ralph Scott, James Breckwoldt, Marta Miori,

and Phillip Schmedeman. Do ais know what the most important issue is?

using language models to code open-text social survey responses at scale.

_Research_ _&_ _Politics_, 11(1):20531680241231468, 2024.

Lisa P Argyle, Ethan C Busby, Nancy Fulda, Joshua R Gubler, Christopher

Rytting, and David Wingate. Out of one, many: Using language models to

simulate human samples. _Political_ _Analysis_, 31(3):337–351, 2023.

Jingqing Zhang, Yao Zhao, Mohammad Saleh, and Peter J. Liu. Pegasus: Pre

training with extracted gap-sentences for abstractive summarization, 2019.

37

Jonathan Chang, Sean Gerrish, Chong Wang, Jordan Boyd-Graber, and David

Blei. Reading tea leaves: How humans interpret topic models. _Advances_ _in_

_neural_ _information_ _processing_ _systems_, 22, 2009.

Justin Grimmer and Brandon M Stewart. Text as data: The promise and pitfalls

of automatic content analysis methods for political texts. _Political_ _analysis_,

21(3):267–297, 2013.

Klaus Krippendorff. Reliability in content analysis: Some common misconcep

tions and recommendations. _Human_ _communication_ _research_, 30(3):411–433,

2004.

DeepSeek-AI, Daya Guo, Dejian Yang, Haowei Zhang, Junxiao Song, Ruoyu

Zhang, Runxin Xu, Qihao Zhu, Shirong Ma, Peiyi Wang, Xiao Bi, Xiaokang

Zhang, Xingkai Yu, Yu Wu, Z. F. Wu, Zhibin Gou, Zhihong Shao, Zhuoshu

Li, Ziyi Gao, Aixin Liu, Bing Xue, Bingxuan Wang, Bochao Wu, Bei Feng,

Chengda Lu, Chenggang Zhao, Chengqi Deng, Chenyu Zhang, Chong Ruan,

Damai Dai, Deli Chen, Dongjie Ji, Erhang Li, Fangyun Lin, Fucong Dai, Fuli

Luo, Guangbo Hao, Guanting Chen, Guowei Li, H. Zhang, Han Bao, Hanwei

Xu, Haocheng Wang, Honghui Ding, Huajian Xin, Huazuo Gao, Hui Qu,

Hui Li, Jianzhong Guo, Jiashi Li, Jiawei Wang, Jingchang Chen, Jingyang

Yuan, Junjie Qiu, Junlong Li, J. L. Cai, Jiaqi Ni, Jian Liang, Jin Chen,

Kai Dong, Kai Hu, Kaige Gao, Kang Guan, Kexin Huang, Kuai Yu, Lean

Wang, Lecong Zhang, Liang Zhao, Litong Wang, Liyue Zhang, Lei Xu, Leyi

Xia, Mingchuan Zhang, Minghua Zhang, Minghui Tang, Meng Li, Miaojun

Wang, Mingming Li, Ning Tian, Panpan Huang, Peng Zhang, Qiancheng

Wang, Qinyu Chen, Qiushi Du, Ruiqi Ge, Ruisong Zhang, Ruizhe Pan, Runji

Wang, R. J. Chen, R. L. Jin, Ruyi Chen, Shanghao Lu, Shangyan Zhou,

Shanhuang Chen, Shengfeng Ye, Shiyu Wang, Shuiping Yu, Shunfeng Zhou,

Shuting Pan, S. S. Li, Shuang Zhou, Shaoqing Wu, Shengfeng Ye, Tao Yun,

38

Tian Pei, Tianyu Sun, T. Wang, Wangding Zeng, Wanjia Zhao, Wen Liu,

Wenfeng Liang, Wenjun Gao, Wenqin Yu, Wentao Zhang, W. L. Xiao, Wei

An, Xiaodong Liu, Xiaohan Wang, Xiaokang Chen, Xiaotao Nie, Xin Cheng,

Xin Liu, Xin Xie, Xingchao Liu, Xinyu Yang, Xinyuan Li, Xuecheng Su,

Xuheng Lin, X. Q. Li, Xiangyue Jin, Xiaojin Shen, Xiaosha Chen, Xiaowen

Sun, Xiaoxiang Wang, Xinnan Song, Xinyi Zhou, Xianzu Wang, Xinxia Shan,

Y. K. Li, Y. Q. Wang, Y. X. Wei, Yang Zhang, Yanhong Xu, Yao Li, Yao

Zhao, Yaofeng Sun, Yaohui Wang, Yi Yu, Yichao Zhang, Yifan Shi, Yiliang

Xiong, Ying He, Yishi Piao, Yisong Wang, Yixuan Tan, Yiyang Ma, Yiyuan

Liu, Yongqiang Guo, Yuan Ou, Yuduan Wang, Yue Gong, Yuheng Zou, Yujia

He, Yunfan Xiong, Yuxiang Luo, Yuxiang You, Yuxuan Liu, Yuyang Zhou,

Y. X. Zhu, Yanhong Xu, Yanping Huang, Yaohui Li, Yi Zheng, Yuchen Zhu,

Yunxian Ma, Ying Tang, Yukun Zha, Yuting Yan, Z. Z. Ren, Zehui Ren,

Zhangli Sha, Zhe Fu, Zhean Xu, Zhenda Xie, Zhengyan Zhang, Zhewen Hao,

Zhicheng Ma, Zhigang Yan, Zhiyu Wu, Zihui Gu, Zijia Zhu, Zijun Liu, Zilin

Li, Ziwei Xie, Ziyang Song, Zizheng Pan, Zhen Huang, Zhipeng Xu, Zhongyu

Zhang, and Zhen Zhang. Deepseek-r1: Incentivizing reasoning capability in

llms via reinforcement learning, 2025. URL `[https://arxiv.org/abs/2501.](https://arxiv.org/abs/2501.12948)`

`[12948](https://arxiv.org/abs/2501.12948)` .

39

### **Appendix** **A Bootstrapping**

**A.1** **Intra-prompt** **stability**

To estimate the confidence intervals for the Intra-prompt stability approach,

we resample the data with replacement, and calculate _αj_ for each bootstrap

sample. We then repeat this process for an arbitrary number of bootstrap

samples (here: 1000). Finally, we calculate the confidence interval from the

distribution of bootstrap samples of _αj_ . The resulting confidence intervals can

then be averaged across iterations to observe trends in prompt stability:

```
   CI _α_ cumulative _,k_ = _α_ cumulative _,k −_ _Z ·_ ~~_√_~~ _[σ][α]_
```

_k_

_, α_ cumulative _,k_ + _Z ·_ ~~_√_~~ _[σ][α]_
_k_ _k_

where _σα_ is the standard deviation of _αj_ from the bootstrap samples, and

_Z_ is the critical value from the standard normal distribution corresponding to

the desired confidence level (here: 1.96, i.e., 95%). For

**A.2** **Inter-prompt** **stability**

On the Inter-prompt stability approach, for each prompt variation _pv_, we re
sample the data with replacement and calculate _αj_ [(] _[p][v]_ [)] for each bootstrap sam

ple. We then repeat this process for an arbitrary number of bootstrap samples

(here: 1000). Finally, we calculate the confidence interval from the distribution

of bootstrap samples of _αj_ [(] _[p][v]_ [)] .

The confidence interval for the average reliability score for prompt variation

_pv_ after _k_ iterations is given by:

```
 CI _α_ (avg _pv,k_ ) [=] _α_ avg [(] _[p][v]_ [)] _,k_ _[−]_ _[Z][ ·]_ _[σ][α]_ ~~_√_~~ [(] _[pv]_ [)]
```

_k_

_[pv]_ [)] _, α_ avg [(] _[p][v]_ [)] _,k_ [+] _[ Z][ ·]_ _[σ][α]_ ~~_√_~~ [(] _[pv]_ [)]

_k_ _k_

A1

where _σα_ ( _pv_ ) is the standard deviation of _αj_ [(] _[p][v]_ [)] from the bootstrap samples,

and _Z_ is the critical value for the confidence level of the intervals.

### **B Additional figures**

A2

Figure B.1: Combined original intra-prompt stability scores.

Figure B.2: Unique annotations by dataset and iteration.

Figure B.3: Combined original inter-prompt stability scores.

Figure B.4: Unique annotations by dataset and temperature.

### **C LM Costs**

Table C.1: Estimated Total API Cost for Various Models

Model input ~~p~~ rice output ~~p~~ rice cost ~~i~~ nput cost ~~o~~ utput total ~~c~~ ost

gpt-4o-mini 0.15 0.60 45.96 1.89 47.85
gpt-4o 2.50 10.00 765.98 31.44 797.42
o1-mini 1.10 4.40 337.03 13.83 350.86
o1 15.00 60.00 4595.86 188.64 4784.51
o3-mini 1.10 4.40 337.03 13.83 350.86

claude-3.5-haiku 0.80 4.00 245.11 12.58 257.69
claude-3.5-sonnet 3.00 15.00 919.17 47.16 966.33
deepseek-v3 0.14 0.28 42.89 0.88 43.78
deepseek-r1 0.55 2.19 168.52 6.89 175.4
gemini-1.5-flash 0.15 0.60 45.96 1.89 47.85

gemini-1.5-pro 1.25 5.00 382.99 15.72 398.71
mistral-small 0.20 0.60 61.28 1.89 63.16
mistral-large 2.00 6.00 612.78 18.86 631.65

### **D Package**

1 `Function` `baseline_stochasticity (original_text,` `prompt_postfix,`

```
    iterations, bootstrap_samples, plot, save_path, save_csv):

```

2

3 `#` `Combine` `original` `text` `and` `prompt` `postfix` `to` `create` `the` `full`

```
    prompt

```

4 `prompt` `=` `original_text` `+` `"` `"` `+` `prompt_postfix`

5

6 `#` `Initialize` `a` `list` `to` `store` `all` `annotations`

7 `all_annotations` `=` `[]`

8

9 `#` `Dictionary` `to` `store` `Krippendorff ’s` `Alpha` `(KA)` `scores`

10 `ka_scores` `=` `{}`

11

12 `#` `Repeat` `the` `process` `for` `a` `given` `number` `of` `iterations`

13 `For` `each` `iteration` `i` `in` `iterations:`

A7

14 `annotations` `=` `[]`

15 `#` `Annotate` `each` `piece` `of` `data` `using` `the` `annotation` `function`

16 `For` `each` `data` `point` `d` `in` `data:`

17 `annotation` `=` `annotate(d,` `prompt)`

18 `annotations.append ({` `id,` `text,` `annotation,` `iteration:` `i`

```
    })

```

19 `all_annotations .extend( annotations )`

20

21 `#` `Convert` `all` `annotations` `to` `a` `DataFrame`

22 `all_annotated` `=` `convert_to_dataframe ( all_annotations )`

23

24 `#` `Calculate` `KA` `scores` `using` `bootstrapping` `for` `increasing`

```
    iterations

```

25 `For` `each` `iteration` `i` `in` `1` `to` `iterations :`

26 `mean_alpha,` `(ci_lower,` `ci_upper)` `=`

27 `bootstrap_krippendorff ( all_annotated` `where` `iteration` `<=`

```
     i,

```

28 `’iteration ’` `,` `bootstrap_samples )`

29 `ka_scores[i]` `=` `{Average` `Alpha:` `mean_alpha,` `CI` `Lower:`

```
    ci_lower,

```

30 `CI` `Upper:` `ci_upper}`

31

32 `#` `Save` `annotated` `data` `to` `CSV` `if` `specified`

33 `If` `save_csv:`

34 `save` `all_annotated` `to` `save_csv`

35

36 `#` `Plot` `KA` `scores` `if` `specified`

37 `If` `plot:`

38 `Plot` `KA` `scores` `with` `CI`

39

40 `Return` `ka_scores,` `all_annotated`

Listing 1: Intra-prompt stability scratch function

1 `Function` `interprompt_stochasticity (original_text,` `prompt_postfix,`

```
    nr_variations, temperatures, iterations, bootstrap_samples,

```

A8

```
    print_prompts, edit_prompts_path, plot, save_path, save_csv):

```

2

3 `#` `Dictionary` `for` `KA` `scores`

4 `ka_scores` `=` `{}`

5

6 `#` `List` `for` `all` `annotated` `data`

7 `all_annotated` `=` `[]`

8

9 `#` `Generate` `paraphrases` `and` `annotate` `data` `for` `each` `temperature`

10 `For` `each` `temperature` `in` `temperatures :`

11 `paraphrases` `=` `generate_paraphrases (original_text,`

```
    prompt_postfix,

```

12 `nr_variations,`

```
    temperature)

```

13 `annotated` `=` `[]`

14 `For` `each` `iteration` `i` `in` `iterations:`

15 `For` `each` `paraphrase` `in` `paraphrases :`

16 `For` `each` `data` `point` `d` `in` `data:`

17 `annotation` `=` `annotate(d,` `paraphrase )`

18 `annotated.append ({` `id,` `text,` `annotation,`

```
    prompt_id,

```

19 `prompt:` `paraphrase,` `original,`

20 `temperature :` `temp })`

21 `annotated_data` `=` `convert_to_dataframe (annotated)`

22 `all_annotated .append( annotated_data )`

23

24 `#` `Calculate` `KA` `scores` `using` `bootstrapping`

25 `mean_alpha,` `(ci_lower,` `ci_upper)` `=`

26 `bootstrap_krippendorff (annotated_data,` `’prompt_id ’` `,`

```
    bootstrap_samples )

```

27 `ka_scores[temp]` `=` `{Average` `Alpha:` `mean_alpha,` `CI` `Lower:`

```
    ci_lower,

```

28 `CI` `Upper:` `ci_upper}`

29

30 `#` `Concatenate` `all` `annotated` `data`

A9

31 `combined_annotated_data` `=` `concatenate_dataframes ( all_annotated )`

32

33 `#` `Save` `annotated` `data` `to` `CSV` `if` `specified`

34 `If` `save_csv:`

35 `save` `combined_annotated_data` `to` `save_csv`

36

37 `#` `Print` `unique` `prompts` `if` `specified`

38 `If` `print_prompts :`

39 `Print` `unique` `prompts`

40

41 `#` `Save` `prompts` `for` `manual` `editing` `if` `specified`

42 `If` `edit_prompts_path :`

43 `Save` `prompts` `to` `edit_prompts_path`

44

45 `#` `Plot` `KA` `scores` `if` `specified`

46 `If` `plot:`

47 `Plot` `KA` `scores` `with` `CI`

48

49 `Return` `ka_scores,` `combined_annotated_data`

Listing 2: Inter-prompt stability scratch function

### **E Prompt variants**

The prompt variants we used for the main analyses can be found at the anonymized

Github repo: `[https://anonymous.4open.science/r/promptstability-7AD3](https://anonymous.4open.science/r/promptstability-7AD3)` .

A10

### **F Original prompts**

```
% Format: Dataset Prompt

tweets_rd_within .csv The following is a Twitter message written

   either by a Republican or a Democrat before the 2020 election.

   Your task is to guess whether the author is Republican or

   Democrat. [Respond 0 for Democrat, or 1 for Republican . Guess

   if you do not know. Respond nothing else .]

tweets_pop_within .csv The following is a Twitter message written

   either by a Republican or a Democrat before the 2020 election.

   Your task is to label whether or not it contains populist

   language. [Respond 0 if it does not contain populist language,

   and 1 if it does contain populist language. Guess if you do

   not know. Respond nothing else .]

news_within.csv The text provided is some newspaper text. Your

   task is to read each article and label its overall sentiment

   as positive or negative. Consider the tone of the entire

   article, not just specific sections or individuals mentioned.

   [Respond 0 for negative, 1 for positive, and 2 for neutral.

   Respond nothing else .]

news_short_within .csv The text provided is some newspaper text.

   Your task is to read each article and label its overall

   sentiment as positive or negative. Consider the tone of the

   entire article, not just specific sections or individuals

   mentioned. [Respond 0 for negative, 1 for positive, and 2 for

   neutral. Respond nothing else .]

manifestos_within .csv The text provided is a party manifesto for

   a political party in the United Kingdom. Your task is to

   evaluate whether it is left -wing or right -wing on economic

   issues. Respond with 0 for left -wing, or 1 for right -wing.

   Respond nothing else.

manifestos_multi_within .csv The text provided is a party

   manifesto for a political party in the United Kingdom.

   Your task is to evaluate where it is on the scale from

   left -wing to right -wing on economic issues. Respond with a

```

A11

```
  number from 1 to 10. 1 corresponds to most left -wing. 10

   corresponds to most right -wing. Respond nothing else.

stance_long_within .csv The text provided come from some tweets

  about Donald Trump. If a political scientist considered the

  above sentence, which stance would she say it held towards

  Donald Trump? [Respond 0 for negative, and 1 for positive.

  Respond nothing else .]

stance_long_within .csv The text provided come from some tweets

  about Donald Trump. If a political scientist considered the

  above sentence, which stance would she say it held towards

  Donald Trump? [Respond 0 for negative, 1 for positive, and 2

  for none. Respond nothing else .]

mii_within.csv Here are some open -ended responses from a

   scientific study of voters to the question what is the most

  important issue facing the country ?. Please assign one of the

  following categories to each open ended text response.

  [Respond 48 for Coronavirus, 15 for Europe, 32 for Living

  costs, 40 for Environment, 26 for Economy -general, and 12 for

   Immigration. Respond nothing else .]

mii_long_within .csv Here are some open -ended responses from a

   scientific study of voters to the question what is the most

  important issue facing the country ?. Please assign one of the

  following categories to each open ended text response.

  [Respond 48 for Coronavirus, 15 for Europe, 32 for Living

  costs, 40 for Environment, 26 for Economy -general, 12 for

  Immigration, 4 for Pol -neg i.e., complaints about politics, 1

  for Health, 31 for Inflation, 22 for War, 5 for Partisan -neg

  i.e., complaints about a party of politician, and 14 for

  Crime. Respond nothing else .]

synth_within .csv In the 2020 presidential election, Donald

  Trump is the Republican candidate, and Joe Biden is the

   Democratic candidate. The following is some information about

  an individual voter. I want you to tell me how you think they

  voted. [Respond 0 for Biden, or 1 for Trump. Guess if you do

  not know. Respond nothing else .]

```

A12

```
synth_short_within .csv In the 2020 presidential election, Donald

  Trump is the Republican candidate, and Joe Biden is the

  Democratic candidate. The following is some information about

  an individual voter. I want you to tell me how you think they

  voted. [Respond 0 for Biden, or 1 for Trump. Guess if you do

  not know. Respond nothing else .]

```

Listing 3: Original prompts

A13
