# **Can Large Language Models Capture Human Annotator Disagreements?**

**Anonymous ACL submission**

**001** **Abstract**

**002** Human annotation variation (i.e., annotation

**003** disagreements) is common in NLP and often

**004** reflects important information such as task sub
**005** jectivity and sample ambiguity. While Large

**006** Language Models (LLMs) are increasingly

**007** used for automatic annotation to reduce hu
**008** man effort, their evaluation often focuses on

**009** predicting the majority-voted “ground truth” la
**010** bels. It is still unclear, however, whether these

**011** models also capture informative human anno
**012** tation variation. Our work addresses this gap

**013** by extensively evaluating LLMs’ ability to pre
**014** dict annotation disagreements without access

**015** to repeated human labels. Our results show that

**016** LLMs struggle with modeling disagreements,

**017** which can be overlooked by majority label
**018** based evaluations. Notably, while RLVR-style [1]

**019** reasoning generally boosts LLM performance,

**020** it degrades performance in disagreement pre
**021** diction. Our findings highlight the critical need

**022** for evaluating and improving LLM annotators

**023** in disagreement modeling. [2]

**024** **1** **Introduction**

**025** The field of NLP rests on annotations where inter
**026** annotator disagreement is common (Snow et al.,

**027** 2008). Such disagreement is often treated as in
**028** convenient noise due to human error, “solved” by

**029** majority voting (Sabou et al., 2014) or expert ag
**030** gregation (Hovy et al., 2013).

**031** These ad-hoc solutions may be misguided, as

**032** annotation disagreement can signal a diversity of

**033** views and is often valuable information (Plank,

**034** 2022). Human annotators have access to differ
**035** ent information sets and are guided by different

**036** value systems (Fornaciari et al., 2021; Fuchs et al.,

**037** 2021). It is therefore not surprising that differ
**038** ent annotators give different answers, in particular

1Reinforcement learning with verifiable rewards (Lambert
et al., 2025; DeepSeek-AI, 2025)
2We will fully open-source our code, data, and LLM generations.

for subjective tasks such as hate speech detection **039**
(e.g. Kennedy et al., 2018) where disagreement **040**
often arises from varying sociodemographic and **041**
cultural backgrounds (Fleisig et al., 2023). Even **042**
seemingly “objective” labeling tasks, such as part- **043**
of-speech (POS) tagging, show disagreement due **044**
to ambiguous language [3] (Plank et al., 2014; Jiang **045**
and de Marneffe, 2022). Generally speaking, dis- **046**
agreement is natural, contains valuable informa- **047**
tion, and should not be ignored or erased, but ac- **048**
tively modeled (Uma et al., 2021; Leonardelli et al., **049**
2023). To model annotator disagreement, previous **050**
work has trained models on datasets with multi- **051**
ple annotations per data point, or used behavioral / **052**
sociodemographic information for annotator mod- **053**
eling (Mostafazadeh Davani et al., 2022; Fleisig **054**
et al., 2023; Hu and Collier, 2024; Giorgi et al., **055**
2024; Chochlakis et al., 2024, 2025; Orlikowski **056**
et al., 2025). **057**
All of the above require the existence of multiply- **058**
annotated data. But what about datasets and emer- **059**
gent tasks [4] that lack repeated human labels? Col- **060**
lecting repeated human labels can be expensive. **061**
LLMs might prove a reasonable substitute for hu- **062**
man annotation, especially given their general ef- **063**
fectiveness in text classification (Pangakis et al., **064**
2023a; Törnberg, 2024; He et al., 2024b), judging **065**
chatbot preferences (Lee et al., 2024), and simulat- **066**
ing human opinion (Meister et al., 2024b; Anthis **067**
et al., 2025). However, the performance of these **068**
LLM annotators is evaluated against a majority la- **069**
bel or agreement with humans (He et al., 2024b; Ni **070**
et al., 2024). In that setup, pointwise estimates are **071**
more important than label distributions, so whether **072**
they can capture human annotation disagreement **073**
remains an open question. Therefore, we identify **074**
the following **practice-evaluation gap** : **075**

3E.g., there might be disagreement in the POS tagging of
“I saw her _duck_ .” as duck can either be a noun or verb.
4For example, LLM generation evaluation (Zheng et al.,
2023\) in emergent applications.

1

**076**

_While LLM annotators are widely studied and_
_deployed, there is no evaluation of whether they_
_can capture informative human disagreements._

**077** Such evaluation can be particularly important for

**078** LLMs optimized on tasks with single-deterministic

**079** answers (e.g., RL with verifiable rewards), which

**080** contrasts with the reality that many annotation tasks

**081** involve multiple valid perspectives. Presumably,

**082** training and evaluation with LLM-annotated data

**083** that ignore human disagreement may run counter to

**084** efforts toward calibrated and pluralistically aligned

**085** AI (Sorensen et al., 2024). In other words: rather

**086** than measuring whether LLMs can reproduce the

**087** majority opinion, we want to know whether they

**088** can reproduce the distribution over human answers.

**089** To address this gap, we evaluate LLMs’ ability

**090** to predict human disagreement in different NLP

**091** annotation tasks, following the recommendations

**092** of Meister et al. (2024b) to predict human opinion

**093** distributions with LLMs. Specifically, we evalu
**094** ate various training paradigms: LLMs trained with

**095** RLVR or RLHF [5], along with other factors: (1) dis
**096** tribution expression (Tian et al., 2023; Wei et al.,

**097** 2024); (2) few-shot learning; and (3) scaling ef
**098** fects of LLM size. We evaluate all settings on

**099** two dimensions: (1) _variance correlation_ (VarCorr,

**100** Mostafazadeh Davani et al., 2022), measuring how

**101** well the LLM-predicted variance correlates to hu
**102** man annotation variance; and (2) _distributional_

**103** _alignment_ (DistAlign, Meister et al., 2024a), di
**104** rectly comparing the distributional divergence of

**105** LLM and human labels.

**106** Our comprehensive evaluation spans 12 prompt
**107** ing settings, 10 LLMs (ranging from 8B to 671B),

**108** and 5 widely studied datasets. We find that RLVR
**109** style reasoning significantly harms disagreement

**110** prediction when human annotation variance is

**111** high. Moreover, forcing additional reasoning ef
**112** fort (Muennighoff et al., 2025) does not improve

**113** the performance of RLVR LLMs. In contrast, for

**114** RLHF LLMs, Chain-of-Thought (CoT, Wei et al.,

**115** 2023) reasoning significantly improves disagree
**116** ment prediction. Furthermore, RLVR LLMs are

**117** better with a _deterministic_ goal (e.g., predicting

**118** the majority annotation) than with a _probabilistic_

**119** goal (e.g., predicting the proportion of human dis
**120** agreements). Our findings suggest that using LLM

**121** annotators—especially with RLVR LLMs and sub
**122** jective tasks—requires extra caution, as these mod
**123** els may overlook critical human disagreements. In

5RLHF refers to LLMs with RL from human feedback
(Ouyang et al., 2022) but without test-time scaling on RLVR.

summary, our contributions are: **124**

1. We extensively evaluate using LLMs to predict **125**
   annotation disagreement. **126**

1. We reveal limitations of reasoning (RLVR) **127**
   LLMs in disagreement prediction (§ 6.2). **128**

1. Our evaluation offers insights into distribution **129**
   expression methods (§ 6.1), reasoning (§ 6.2), **130**
   the importance of human annotations (§ 6.3), **131**
   few-shot steering (§ 6.4), and model scale **132**
   (§ 6.5). **133**

**2** **Related Work** **134**

**Annotation** **Disagreement** **in** **NLP.** Annotation **135**
disagreement has been an important area of study **136**
with long history (Wiebe et al., 2004; Ovesdot- **137**
ter Alm, 2011; Basile et al., 2021; Uma et al., 2021; **138**
Leonardelli et al., 2023). Various qualitative and **139**
quantitative analyses show that the majority of dis- **140**
agreement is caused by other systematic reasons **141**
(e.g., ambiguity, context sensitivity etc.) rather than **142**
random annotation noise (e.g., carelessness) (Plank **143**
et al., 2014; Popovi´c, 2021; Jiang and de Marneffe, **144**
2022; Santy et al., 2023; Zhang et al., 2024). **145**
Prior work in modeling disagreement mainly fo- **146**
cuses on datasets with repeated annotations and **147**
annotator information (e.g., annotator ID and so- **148**
ciodemographic features), which can be used for **149**
annotator modeling (Mostafazadeh Davani et al., **150**
2022; Hu and Collier, 2024; Giorgi et al., 2024; **151**
Chochlakis et al., 2024, 2025; Orlikowski et al., **152**
2025). However, emergent tasks (e.g., chatbot **153**
preference) often lack human annotations (e.g., Ul- **154**
traFeedback, Cui et al., 2024) due to the cost of **155**
human data collection and the need for scalabil- **156**
ity, making it even harder to obtain disagreements **157**
with multiple human annotators. Even when mul- **158**
tiple annotations are available (e.g., HelpSteer2, **159**
Wang et al., 2025b), annotator information might **160**
be missing, making it challenging to model individ- **161**
ual annotators’ behavior or persona. Therefore, it **162**
is important to evaluate LLM annotators’ ability to **163**
capture disagreement without modeling extensive **164**
repeated human labels. **165**

**Distribution Prediction with LLM.** The extensive **166**
training corpus of LLMs may enable them to sim- **167**
ulate different opinions and predict distribution in **168**
real-world (Grossmann et al., 2023; Ziems et al., **169**
2024), and numerous previous studies use LLMs to **170**
predict the distribution of political opinions (Argyle **171**
et al., 2023; Durmus et al., 2024; Karanjai et al., **172**

2

**173** 2025; Jiang et al., 2025). Meister et al. (2024b)

**174** highlight that the performance of distribution pre
**175** diction is highly dependent on the target task (e.g.,

**176** political vs. non-political). Hence, we extend the

**177** evaluation of distribution prediction to disagree
**178** ment in NLP annotation, an interesting yet under
**179** explored area in existing work. We also evaluate

**180** the under-studied role of LLM scale and test-time

**181** reasoning in distribution prediction.

**182** **Automatic Annotation.** Despite the prevalence of

**183** LLM-automated annotation (Tan et al., 2024), its

**184** evaluation ignores disagreement modeling. LLM

**185** annotators are evaluated by accuracy (He et al.,

**186** 2024b; Törnberg, 2023), downstream fine-tuning

**187** performance (Lee et al., 2024; Ni et al., 2024,

**188** 2025), and agreement with human annotators (He

**189** et al., 2024a; Ni et al., 2024). An LLM annotator

**190** is validated as reliable if it achieves higher average

**191** agreement with human than inter-human agreement

**192** (Ni et al., 2024; Calderon et al., 2025). However,

**193** this justification ignores the rich information in dis
**194** agreement between humans. To the best of our

**195** knowledge, no prior work has evaluated the LLMs’

**196** ability in simulating a group of annotators and pre
**197** dicting the annotation distribution.

**198** **3** **Problem Formalization**

**199** In this section, we formalize the problem of predict
**200** ing human annotation disagreement and visualize

**201** it in Fig. 1. Let _d_ _∈_ _D_ be a datapoint from a

**202** dataset _D_, for which we have a set of _n_ annotations

**203** **Ad** = _{ad,i|ad,i_ _∈{_ 0 _,_ 1 _}, i_ _∈{_ 1 _,_ 2 _, ..., n}}_ from

**204** different human annotators, indicating if _d_ is a pos
**205** itive (1) or negative (0) sample. [6] We assume that

6For simplicity, we study the binary classification problem.
Multi-label classification problem with _m_ labels is equivalent
to _m_ binary classification problems.

the _n_ annotators are representative of the annotator **206**
population, so human annotation on _d_ follows a **207**
Bernoulli distribution _Hd_ parameterized by: **208**

[= 1] _[|][a][d,i]_ _[∈]_ **[A][d]** _[}|]_
_pd_ = _[|{][a][d,i]_ (1) **209**

_n_

where _pd_ denotes the probability that a human an- **210**
notator labels _d_ positive. The variance of human **211**
annotation is _σd_ [2] [=] _[ p][d]_ [(1] _[ −]_ _[p][d]_ [)][.] **212**
Given human disagreement as the gold label, a **213**
machine learning algorithm is tasked with simulat- **214**
ing and predicting it. Specifically, through tech- **215**
niques such as fine-tuning, prompting, or sampling, **216**
a model can predict a Bernoulli distribution _H_ [ˆ] _d_ **217**
regarding how likely a human will annotate _d_ posi- **218**
tive, parameterized by _p_ ˆ _d_ . Then, the variance of the **219**
machine-predicted annotation is _σ_ ˆ _d_ [2] [=] _[p]_ [ˆ] _[d]_ [(1] _[ −]_ _[p]_ [ˆ] _[d]_ [)][.] **220**
To evaluate the model’s annotation distribution **221**
against humans’, we employ two dimensions of **222**
evaluation from prior work: **223**

**Variance** **Correlation.** In automatic annotation, **224**
it is crucial for LLMs to identify samples that are **225**
likely to elicit disagreements between human an- **226**
notators. To evaluate this ability, we adopt the **227**
variance correlation metric from Mostafazadeh Da- **228**
vani et al. (2022), which quantifies to what extent **229**
higher model uncertainty indicates higher human **230**
uncertainty. The formula is: **231**

```
      -           VarCorr = Corr _⟨σd_ [2] _[⟩][d][∈][D][,][ ⟨][σ]_ [ˆ] _d_ [2] _[⟩][d][∈][D]_ (2) **232**
```

where Corr denotes the Pearson’s Correlation (Pear- **233**
son, 1895). **234**

**Distributional Alignment.** Although VarCorr cap- **235**
tures the alignment of uncertainty, it fails to cap- **236**
ture the exact gap between the annotation distribu- **237**
tions. For example, if _⟨pd⟩d∈D_ = _⟨_ 0 _._ 4 _,_ 0 _._ 5 _⟩_ and **238**

3

**239** _⟨p_ ˆ _d⟩d∈D_ = _⟨_ 0 _._ 1 _,_ 0 _._ 2 _⟩_, the model achieves perfect

**240** VarCorr but underestimates the human disagree
**241** ment. Similarly, _⟨pd,_ ˆ _pd⟩_ = _⟨_ 0 _._ 2 _,_ 0 _._ 8 _⟩_ shares the

**242** same variance, but has contradictory distribution.

**243** Therefore, we adopt Distributional Alignment from

**244** Meister et al. (2024b), formalized by:

1
DistAlign =
_|D|_

**245** DistAlign = _∥pd −_ _p_ ˆ _d∥_ 1 (3)

_|D|_

_d∈D_

**246** which measures the exact difference between

**247** two distributions. Importantly, DistAlign can
**248** not fully substitute VarCorr in evaluating uncer
**249** tainty. For example, given the gold labels of sam
**250** ples _⟨p_ 1 _, p_ 2 _⟩_ = _⟨_ 0 _._ 33 _,_ 0 _._ 4 _⟩_, model prediction (A)

**251** _⟨p_ ˆ1 _,_ ˆ _p_ 2 _⟩_ = _⟨_ 0 _._ 4 _,_ 0 _._ 33 _⟩_ is better than (B) _⟨p_ ˆ1 _,_ ˆ _p_ 2 _⟩_ =

**252** _⟨_ 0 _._ 15 _,_ 0 _._ 4 _⟩_ in DistAlign. However, (B) has better

**253** VarCorr than (A) and correlates better with human

**254** uncertainty.

**255** Therefore, both VarCorr and DistAlign are im
**256** portant dimensions to evaluate the prediction of

**257** disagreement.

**258** **F1** **on** **Majority** **Label.** LLMs (especially with

**259** RLVR) are optimized to predict the majority la
**260** bels. Therefore, we adopt F1-score to study the

**261** difference between disagreement prediction and

**262** majority label prediction. Specifically, we compute

**263** F1( _⟨_ 1 _{pd_ _>_ 0 _._ 5 _}⟩d∈D, ⟨_ 1 _{p_ ˆ _d_ _>_ 0 _._ 5 _}⟩d∈D_ ) where

**264** 1 is the indicator function. We drop data points

**265** with _pd_ or _p_ ˆ _d_ equal to 0 _._ 5 to avoid biased tie-break.

**266** **4** **Datasets**

**267** Hate speech detection (Warner and Hirschberg,

**268** 2012; Waseem, 2016) and emotion classification

**269** (Hirschberg et al., 2003; Mihalcea and Liu, 2006)

**270** are two broadly studied tasks in annotation dis
**271** agreement. We follow Mostafazadeh Davani et al.

**272** (2022) and include Gab Hate Corpus (hereafter

**273** GHC; Kennedy et al., 2018) and GoEmotions

**274** (Demszky et al., 2020) for our evaluation. GoE
**275** motion is a multi-label classification dataset. We

**276** divide it into three binary classification problems—

**277** annotating whether a post contains (1) positive /

**278** negative / ambiguous emotions, or not (0). GoEmo
**279** tion Subtasks hereafter referred to as Pos, Neg, and

**280** Amb. Furthermore, we include HelpSteer2 (here
**281** after HS2; Wang et al., 2025b), which consists of

**282** multiple annotators’ preferences for the helpfulness

**283** of chatbot responses. Therefore, our evaluation in
**284** cludes five tasks: hate speech detection, chatbot

**285** preference classification, and classifications of pos
**286** itive, negative, and ambiguous emotions.

We further derive two subsets of interest from **287**
the dataset of each task: (1) Random subset: a ran- **288**
domly sampled subset with 1k data points; and **289**
(2) HighVar subset: a subset of 200 [7] data points **290**
where at least two annotators disagree with the **291**
majority label, and where the overall proportion **292**
of the minority label (1 _−_ _pd_ ) falls between [1] 3 **293**

and [1] 2 [to ensure high annotation variance.] [Random] **294**

keeps the original data distribution, containing a **295**
lot of samples where human achieves agreement **296**
and certain samples where human disagrees. It **297**
is useful for evaluating VarCorr—how a model is **298**
helpful in predicting human annotation variance. **299**
HighVar contains samples with potential system- **300**
atic disagreement (e.g., two annotators disagree **301**
with the other three). Therefore, it is useful in **302**
evaluating DistAlign—when there exist separate **303**
opinions, can a model detect that and predict an **304**
aligned distribution? Dataset preparation details **305**
can be found in App. A. **306**
Notably, we do not evaluate F1 and VarCorr on **307**
HighVar, as predicting majority labels or annota- **308**
tion variance is ill-defined when human annotators **309**
already exhibit high annotation variance. **310**

**5** **Methodology** **311**

To effectively evaluate LLMs’ ability in disagree- **312**
ment prediction, it is important to prompt them **313**
correctly. Therefore, we first survey previous work **314**
to identify promising distribution prediction meth- **315**
ods worth exploring in our evaluation (§ 5.1). Then **316**
we describe the implementation details of these **317**
methods and relevant baselines (§ 5.2). **318**

**5.1** **Existing Methods for LLM Distribution** **319**
**Prediction** **320**

**Distribution** **Expression** **Method.** Literature in **321**
LLM calibration suggests two approaches for LLM **322**
to express a distribution: (1) asking for a verbalized **323**
probability (Tian et al., 2023); and (2) sampling **324**
multiple LLM responses and using the answer fre- **325**
quency as the probability. Tian et al. (2023) show **326**
that a verbalized distribution is better, while Wei **327**
et al. (2024) draw an opposite conclusion. In dis- **328**
tribution prediction, Meister et al. (2024b) finds **329**
that verbalized distributions achieve good perfor- **330**
mance, but sampling-based distributions remain **331**
underexplored, especially when combined with rea- **332**
soning. Therefore, we explore both verbalized and **333**

7Size of HighVar is determined by the limited number
of data points with at least two disagreements. The size of
Random is determined for budget control.

4

**334** sampling-based distribution expression methods.

**335** **The** **Effects** **of** **Reasoning.** Test-time reasoning

**336** significantly enhances LLM performance in deter
**337** ministic reasoning tasks like math and code gener
**338** ation (Wei et al., 2023; DeepSeek-AI, 2025). How
**339** ever, no previous work explores the role of reason
**340** ing in probabilistic annotation disagreement. On

**341** one hand, reasoning can benefit the prediction of

**342** disagreements by giving LLMs the chance to ex
**343** plore and compare different opinions; on the other

**344** hand, reasoning may harm decision making, espe
**345** cially when the problem is subjective or has hard
**346** to-articulate criteria (Nordgren and Dijksterhuis,

**347** 2009; Liu et al., 2024). In this work, we compare

**348** three settings: RLHF LLMs with and without CoT,

**349** and RLVR-style reasoning.

**350** **In-Context Steering Methods.** In-context steering

**351** refers to providing LLMs with information about

**352** the target group being simulated to help distribution

**353** prediction. We investigate the impact of few-shot

**354** prompting on predicting annotation disagreement,

**355** a method shown effective by previous work (Meis
**356** ter et al., 2024b). Other common steering methods

**357** include persona steering (Santurkar et al., 2023)

**358** and annotator modeling (Chochlakis et al., 2024,

**359** 2025). However, we do not include these methods

**360** because (1) for many tasks (e.g., chatbot prefer
**361** ence), demographic information might have limited

**362** relevance to disagreements, and annotator informa
**363** tion might often be unavailable; and (2) piror work

**364** has highlighted notable limitations in both prompt
**365** based annotator modeling (Chochlakis et al., 2024,

**366** 2025) and persona steering (Meister et al., 2024b;

**367** Hu and Collier, 2024).

**368** **5.2** **Implementation Details**

**369** **Prompt-Based** **Methods.** We evaluate the com
**370** binations of promising settings discussed in the

**371** previous section—namely, the combinations of (1)

**372** with or without few-shot steering; (2) verbalized or

**373** sampling-based distribution; and (3) RLHF LLMs

**374** with or without CoT, or using RLVR LLMs instead.

**375** Hence, there are 2 _×_ 2 _×_ 3 = 12 settings to be

**376** evaluated in total.

**377** To make RLHF and RLVR LLMs comparable,

**378** we use DeepSeek-R1 series LLMs (DeepSeek-AI,

**379** 2025) (e.g., DeepSeek-R1-Distill-Llama-70B) and

**380** corresponding RLHF LLMs sharing the same base

**381** LLM (e.g., Llama-3.3-70B-Instruct). To investi
**382** gate the effect of scaling in LLM size, we experi
**383** ment LLMs of 8B, 14B, 32B, 70B, and 671B pa

rameters [8] . **384**
The prompt structure is illustrated in Fig. 1. For **385**
few-shot illustration, We carefully balance the 5 **386**
examples—2 of human-agreed positives and nega- **387**
tives correspondingly, and 1 human-disagreed—to **388**
avoid introducing spurious bias (Turpin et al., 2023) **389**
to distribution prediction. For verbalized probabil- **390**
ity, we follow Meister et al. (2024b) to directly ask **391**
for the proportion of human annotators that may **392**
annotate the sample positive. For sampling-based **393**
distributions, we ask for the most likely human la- **394**
bel and sampling 10 times with a temperature of **395**
0.7 for conventional LLMs, and 0.6 for reasoning **396**
LLMs, following the official recommendation. **397**
Furthermore, all prompts present LLMs with **398**
the same annotation guidelines as in the original **399**
dataset papers, which are likely the guidelines pre- **400**
sented to human annotators. This may increase **401**
LLMs’ chance to capture human disagreement **402**
caused by the context or natural ambiguity of anno- **403**
tation guidelines. We also explicitly prompt LLMs **404**
to assess potential disagreement and consider con- **405**
text sensitivity (e.g., cultural, social, linguistic am- **406**
biguity) that may influence the interpretation. Full **407**
prompts and inference hyperparameter / budget are **408**
detailed in App. B and App. C respectively. **409**

**Fine-tuning Methods.** Fine-tuning encoder-only **410**
LMs for disagreement prediction is a straightfor- **411**
ward way to use human labels (Mostafazadeh Da- **412**
vani et al., 2022; Fleisig et al., 2023). Therefore, we **413**
fine-tune ModernBERT-large (Warner et al., 2024) **414**
and DeBERTa-V3-large (He et al., 2023) to regress **415**
onto the positive annotation probability of human **416**
_pd_ . The loss function is: **417**

1
_L_ MSE =
_|D_ train _|_

(ˆ _pd −_ _pd_ ) [2] (4) **418**
_d∈D_ train

where ˆ _pd_ = LM( _d_ ) is the prediction of the encoder- **419**
only LM; and _D_ train denotes a randomly sampled **420**
training set. Fine-tuning baselines require thou- **421**
sands of data points and repeated human labels **422**
to capture the target distribution. This is not ap- **423**
plicable for most automatic annotation tasks with **424**
limited human labels without majority voting ag- **425**
gregation. Fine-tuning details are in App. D. **426**

**6** **Results** **427**

This section presents the evaluation results and **428**
takeaways. We start from comparing distribution **429**

8We exclude 7B LLMs because their base LLM, Qwen2.57B-Math, is specialized for mathematical tasks and therefore
unsuitable for the current task.

5

Random Random Random HighVar
**VarCorr** **DistAlign** **F1** **DistAlign**

_Verbalized > Sampling:_

95.0% _[∗∗]_ 92.5% _[∗∗]_ 28.3% _[∗∗]_ 98.3% _[∗∗]_

_RLVR > RLHF:_

40.0% 62.0% _[∗]_ 36.0% _[∗∗]_ 18.0% _[∗∗]_

_RLHF CoT > RLHF w/o CoT :_

64.0% _[∗∗]_ 72.0% _[∗∗]_ 66.0% _[∗∗]_ 70.0% _[∗∗]_

_Extend Reasoning Once > Natural Ending :_

62.50% 65.00% _[∗]_ 47.50% 60.00%
_Extend Reasoning Twice > Natural Ending :_

60.00% 72.50% 50.00% 57.50%
_w/ > w/o Few-Shot:_

_HS2 w/ > w/o Few-Shot:_

26.67% _[∗∗]_ 0.00% _[∗∗]_ 6.67% _[∗∗]_ 0.00% _[∗∗]_

_GHC w/ > w/o Few-Shot:_

80.00% _[∗∗]_ 80.00% _[∗∗]_ 66.67% _[∗∗]_ 53.33%
_GE-Pos w/ > w/o Few-Shot:_

53.33% 60.00% 33.33% _[∗∗]_ 66.67% _[∗∗]_

_GE-Neg w/ > w/o Few-Shot:_

53.33% 53.33% 26.67% _[∗∗]_ 53.33%
_GE-Amb w/ > w/o Few-Shot:_

_Positive > Negative Scaling:_

Table 1: Win rates of the left settings with Wilcoxon
signed-rank tests. We evaluate on the Random and
HighVar subsets. The intensity of green and red indicates how strongly the left setting wins over or loses
to the right one. Statistically significant wins or losses
are marked with _[∗∗]_ ( _p \<_ 0 _._ 01) and _[∗]_ ( _p \<_ 0 _._ 05).

**430** expression methods—verbalized vs. sampling
**431** based distribution. Then, we investigate the role of

**432** steering method and different reasoning paradigms.

**433** Due to the large number of experiments, we present

**434** aggregated results to convey core messages and

**435** present the full model-level performance in App. E.

**436** **6.1** **Verbalizing or Sampling?**

**437** We compare verbalized and sampling-based distri
**438** butions across 120 controlled experimental settings,

**439** varying only the distribution expression method.

**440** These settings span 4 LLM sizes (8B, 14B, 32B,

**441** and 70B [9] ), 3 reasoning paradigms (RLVR, RLHF

**442** with and without CoT), 5 datasets, and 2 steering

**443** strategies (few-shot or no steering).

**444** The winning rates of the verbalized distribution

**445** in different metrics are shown in the first row of

**446** Table 1, combined with the results of the Wilcoxon

**447** test (Wilcoxon, 1992) to show statistical signif
**448** icance. We observe that the verbalized method

**449** significantly outperforms in predicting annotation

**450** distribution (VarCorr and DistAlign). However, the

9We exclude the 671B model due to the high cost of
sampling-based prediction.

sampling-based method is better in predicting the **451**
majority label (F1). This indicates that predicting **452**
the majority label and disagreement are different **453**
tasks that require separate evaluations. **454**
_**Takeaway:**_ we recommend using verbalized dis- **455**
tribution in disagreement prediction, and evaluat- **456**
ing LLM annotators on both majority label and **457**
disagreement prediction—especially those rely on **458**
sampling-based self-consistency to improve major- **459**
ity label prediction (Pangakis et al., 2023b; Ni et al., **460**
2024; Zhou et al., 2025; Wang et al., 2025a). **461**
Given the significantly better performance of **462**
verbalized distribution, we focus the analyses in **463**
the following sections on results obtained with this **464**
method. Sampling-based methods yield better ma- **465**
jority label prediction, which lies outside the scope **466**
of disagreement prediction. We therefore analyze **467**
those results separately in App. F. **468**

**6.2** **Reasoning in Disagreement Prediction** **469**

We compare reasoning methods—(1) RLHF LLMs **470**
without reasoning; (2) RLHF LLMs with CoT **471**
reasoning; and (3) lengthy reasoning with RLVR **472**
LLMs—across 50 controlled settings, varying only **473**
the reasoning methods. Controlled settings span 5 **474**
LLM sizes (8B, 14B, 32B, 70B, 671B), 5 datasets, **475**
and 2 steering strategies (few-shot or no steering). **476**
Results on Random and HighVar are presented **477**
in Table 2 and Table 3 respectively. We aggregate **478**
the results of 5 LLM sizes by the average and best **479**
scores to enable straightforward comparisons be- **480**
tween reasoning methods. Rows 2 and 3 of Table 1 **481**
present the comparisons of (1) RLVR vs. RLHF **482**
(w/ or w/o CoT); and (2) RLHF w/ vs. w/o CoT **483**
across 50 controlled settings. **484**
When comparing RLVR LLMs with their RLHF **485**
counterparts, we observe that (1) on HighVar **486**
where humans strongly disagree with each other, **487**
RLVR LLMs achieve significantly worse perfor- **488**
mance in both aggregated scores in Table 3 and **489**
setting-level comparisons summarized in Table 1. **490**
(2) On Random, results are more mixed but RLVR **491**
model does not significantly outperform their **492**
RLHF counterparts, as Table 1 row 2 shows. How- **493**
ever, the Table 1 row 3 shows that CoT reasoning **494**
in RLHF LLMs improves the performance on both **495**
Random and HighVar, compared to without CoT. **496**
To better understand the effect of long reason- **497**
ing with RLVR LLMs, we force these models **498**
to think longer by replacing the end of thinking **499**
token “</think>” with “Wait”, which effectively **500**
boosts performance for math reasoning (Muen- **501**

6

|No-CoT 0.143 0.254 0.718<br>Avg CoT 0.177 0.250 0.677<br>R1 0.136 0.247 0.705|0.362 0.229 0.294<br>0.363 0.203 0.373<br>0.374 0.177 0.394|0.183 0.249 0.607<br>0.192 0.226 0.638<br>0.236 0.215 0.633|0.337 0.265 0.561<br>0.329 0.246 0.570<br>0.331 0.242 0.556|0.096 0.273 0.440<br>0.116 0.252 0.431<br>0.121 0.257 0.395|
|---|---|---|---|---|
|Best<br>No-CoT<br>0.183<br>0.236<br>0.741<br>CoT<br>0.230<br>0.231<br>0.715<br>R1<br>0.188<br>0.230<br>0.722|0.461<br>0.158<br>0.376<br>0.399<br>0.164<br>0.434<br>0.426<br>0.148<br>0.463|0.241<br>0.220<br>0.721<br>0.233<br>0.209<br>0.675<br>0.274<br>0.201<br>0.674|0.444<br>0.265<br>0.583<br>0.389<br>0.246<br>0.581<br>0.419<br>0.241<br>0.596|0.126<br>0.256<br>0.547<br>0.183<br>0.230<br>0.534<br>0.147<br>0.233<br>0.463|

_Verbalized Distribution + Few-shot Steering_

|No-CoT 0.098 0.291 0.683<br>Avg CoT 0.139 0.279 0.686<br>R1 0.100 0.281 0.608|0.355 0.205 0.372<br>0.380 0.182 0.405<br>0.416 0.159 0.393|0.197 0.240 0.573<br>0.200 0.226 0.619<br>0.236 0.212 0.589|0.241 0.275 0.526<br>0.321 0.250 0.566<br>0.359 0.233 0.538|0.055 0.306 0.450<br>0.098 0.276 0.450<br>0.107 0.279 0.333|
|---|---|---|---|---|
|Best<br>No-CoT<br>0.163<br>0.258<br>0.710<br>CoT<br>0.182<br>0.266<br>0.692<br>R1<br>0.128<br>0.255<br>0.678|0.459<br>0.142<br>0.553<br>0.436<br>0.147<br>0.467<br>0.449<br>0.135<br>0.447|0.249<br>0.210<br>0.658<br>0.243<br>0.211<br>0.680<br>0.252<br>0.205<br>0.675|0.411<br>0.226<br>0.576<br>0.409<br>0.219<br>0.580<br>0.402<br>0.214<br>0.593|0.088<br>0.268<br>0.534<br>0.135<br>0.248<br>0.512<br>0.118<br>0.267<br>0.437|

Table 2: Performance on Random (randomly sampled) subsets of all datasets, aggregating 8B–671B results by
Average or Best. Color intensity reflects relative performance within each column. RLVR LLMs shows no significant
advantage over RLHF LLMs. Fine-tuning outperforms prompting on all datasets except HS2.

HS2 _↓_ GHC _↓_ Pos _↓_ Neg _↓_ Amb _↓_

Table 3: DistAlign Performance on HighVar (high annotation variance) subset of all datasets. RLVR LLMs
constantly underperforms RLHF LLMs on both Avg
and Best. Fine-tuning outperforms prompting on all
datasets except GHC.

**502** nighoff et al., 2025). We force longer reasoning

**503** twice, and compare to the results to natural ending.

**504** The controlled comparisons span 40 settings—4

**505** LLM sizes [10], 2 steering methods, and 5 datasets.

**506** The row 4 and 5 of Table 1 show the results, where

**507** forcing longer reasoning rarely leads to statistically

**508** significant improvements.

**509** Moreover, RLVR underperforms RLHF on ma
**510** jority label prediction (F1) with verbalized distribu
**511** tion as shown by Table 1. However, when applying

10We exclude the 671B DeepSeek-R1 since this model is
accessed through API, which does not allow forcing longer
reasoning

sampling-based method, RLVR significantly out- **512**
performs RLHF on F1 (win rate 62.5% _[∗∗]_ ). This **513**
may be because, in sampling, LLMs are prompted **514**
to predict the most likely human label (i.e., major- **515**
ity label), while considering disagreement. This **516**
_deterministic_ goal is more suitable for RLVR LLMs **517**
than the _probabilistic_ goal of predicting the propor- **518**
tion of disagreement. However, the sampling-based **519**
method still leads to worse distributional prediction **520**
as discussed in § 6.1. **521**
_**Takeaway:**_ CoT reasoning with RLHF LLMs **522**
may benefit the prediction of disagreement. How- **523**
ever, people should be more cautious about lengthy **524**
reasoning with RLVR LLMs, which can signifi- **525**
cantly harm the performance in probabilistic dis- **526**
agreement prediction. **527**

**6.3** **Human Labels are Important** **528**

To study whether it is necessary to gather repeated **529**
human labels for disagreement modeling, we com- **530**
pare small LMs - ModernBERT and DeBERTa- **531**
V3 – fine-tuned on large-scale human annotations, **532**
to the best LLM results. From Table 2 and Ta- **533**
ble 3, we observe that fine-tuned small encoder- **534**
only LMs outperforms LLMs on GHC Random, **535**
HS2 HighVar, and all GoEmotions subsets, indicat- **536**
ing the value of real human annotations in predict- **537**
ing disagreement. However, LLM-based methods **538**
are also promising, achieving better performance **539**
on HS2 Random and GHC HighVar without human **540**
annotations. **541**
_**Takeaway:**_ incorporating human labels is highly **542**
beneficial for accurate disagreement modeling, **543**
while LLM-based methods also demonstrate strong **544**
potential due to their cost efficiency and solid per- **545**
formance on certain tasks. **546**

7

Table 4: Correlation of performance and log-number of LLM parameters ( _log_ (8) to _log_ (671)). Green and red
intensity reflects the degree of positive / negative scaling.

**547** **6.4** **Few-Shot Steering**

**548** Meister et al. (2024b) show that LLMs exhibit

**549** strong few-shot steerability in distribution predic
**550** tion. Therefore, we investigate whether few-shot

**551** illustrations can steer LLMs for better disagree
**552** ment prediction. Few-shot is compared to zero-shot

**553** prompting across 75 controlled settings—spanning

**554** 5 LLM sizes (8B to 671B), 3 reasoning settings,

**555** and 5 datasets. Comparisons are summarized in the

**556** sixth row of Table 1. Few-shot steering decreases

**557** the performance on 4 metrics, with statistically sig
**558** nificant drop in 3 of them.

**559** Observing Table 2 and Table 3, we notice that

**560** few-shot steering seems to help certain tasks (e.g.,

**561** GHC Random) but harm others (e.g., HS2). There
**562** fore, we separately evaluate the effect of few-shot

**563** steering on each dataset (see the lower half of Ta
**564** ble 1 before the last row). The results show that

**565** few-shot steering significantly harms disagreement

**566** prediction on HS2 and GE-Pos, but improves per
**567** formance on GHC Random and GE-Neg HighVar.

**568** _**Takeaway:**_ few-shot steering can be helpful, but

**569** its effectiveness varies across tasks and datasets.

**570** We also perform similar per-dataset analyses

**571** in earlier sections (e.g., comparing CoT vs. no
**572** CoT), which mostly yield consistent trends with

**573** the aggregated results or lacks statistical signifi
**574** cance. We thus only include the aggregated results

**575** in Table 1 and briefly discuss the per-dataset results

**576** in App. G.

**577** **6.5** **Scaling Effect of LLM Size**

**578** Our coverage of LLMs from 8B to 671B allows

**579** exploring the scaling effect of LLM size in dis
**580** agreement prediction. Specifically, we compute

**581** the correlation between performance improvement

**582** and the increase of log-number of parameters. Ta
**583** ble 4 reports the Pearson’s coefficients spanning

**584** 30 settings—5 datasets, 2 steering methods, and

**585** 3 reasoning settings. The comparison across 30

**586** settings are summarized in the last row of Table 1.

**587** Scaling LLM size can improve disagreement pre

diction with statistical significance. However, the **588**
improvement is less significant on HighVar while **589**
more significant for majority label prediction (F1). **590**
Table 4 also shows that different datasets seem to **591**
have different scaling effect. Conducting Wilcoxon **592**
Test for each dataset, we find that there is statistical **593**
significant negative scaling on the disagreement **594**
prediction of Neg Random. Other trends are consis- **595**
tent with the results observed across all datasets. **596**

_**Takeaway:**_ Scaling LLM size may more effec- **597**
tively boost majority label prediction than disagree- **598**
ment prediction. Negative scaling occurs especially **599**
in cases of strong disagreement (HighVar subsets) **600**
or on specific datasets (e.g., Neg Random). **601**

**7** **Discussion and Conclusion** **602**

LLM annotators are widely used, but their ability to **603**
capture informative human disagreement remains **604**
under-explored. Addressing this gap, we compre- **605**
hensively evaluate LLMs in disagreement predic- **606**
tion, covering widely studied tasks, and common **607**
settings of LLM usage. **608**

RLHF LLMs exhibit greater potential than **609**
RLVR LLMs in predicting disagreements (§ 6.2). **610**
This may be because RLVR optimization on veri- **611**
fiable and deterministic answers harms the ability **612**
to capture multiple debatable answers. In contrast, **613**
reasoning (CoT) with RLHF LLMs improves dis- **614**
agreement prediction, suggesting that the reduced **615**
performance of RLVR is not necessarily due to rea- **616**
soning itself. This may also be related to recent **617**
observations that RLVR models can hallucinate **618**
more than RLHF models in some tasks (Metz and **619**
Weise, 2025). **620**

Moreover, we find that although scaling LLM **621**
size and few-shot steering improve disagreement **622**
prediction, these methods are not more effective **623**
than a data-centric approach—fine-tuning small **624**
LLMs with thousands of human data (§ 6.3). Given **625**
the scarcity of repeated human labels, future work **626**
may explore how to leverage human data more **627**
efficiently. **628**

8

**629** **Limitations**

**630** This work evaluates LLMs in disagreement predic
**631** tion and draws observations with statistical signifi
**632** cance tests. However, it does not analyze the causes

**633** of the observations. For example, what are the ex
**634** act causes of RLVR worse than RLHF LLMs? Why

**635** does few-shot steering work for some datasets but

**636** not others? These questions are critical for provid
**637** ing concrete guidelines for real-world practice. As

**638** the first work studying disagreement modeling in

**639** LLM annotation, we prioritize evaluation **breadth**

**640** to include broad potential settings in reasoning, dis
**641** tribution expression, in-context steering, and LLM

**642** size. This gives us advantages in (1) addressing

**643** promising settings in prior work (§ 5.1); and (2)

**644** conducting a statistical significance check thanks

**645** to the large number of experiments. However, it

**646** also limits us in analysis **depth** and we leave the

**647** critical causal analyses of the observations to future

**648** work.

**649** **Ethics Statement**

**650** **Data** **Privacy** **or** **Bias.** We use publically avail
**651** able datasets (GHC, GoEmotions, and HelpSteer2)

**652** which have no data privacy issues or bias against

**653** certain demographics. All artifacts we use are un
**654** der licenses allowing research usage. We also no
**655** tice no ethical risks associated with this work.

**656** **References**

**657** Jacy Reese Anthis, Ryan Liu, Sean M. Richardson,

**658** Austin C. Kozlowski, Bernard Koch, James Evans,

**659** Erik Brynjolfsson, and Michael Bernstein. 2025. [Llm](https://arxiv.org/abs/2504.02234)

**660** [social simulations are a promising research method.](https://arxiv.org/abs/2504.02234)

**661** _Preprint_, arXiv:2504.02234.

**662** Lisa P. Argyle, Ethan C. Busby, Nancy Fulda, Joshua R.

**663** Gubler, Christopher Rytting, and David Wingate.

**664** 2023. Out of one, many: [Using](https://doi.org/10.1017/pan.2023.2) language mod
**665** els to simulate [human](https://doi.org/10.1017/pan.2023.2) samples. _Political_ _Analysis_,

**666** 31(3):337–351.

**667** Valerio Basile, Michael Fell, Tommaso Fornaciari, Dirk

**668** Hovy, Silviu Paun, Barbara Plank, Massimo Poesio,

**669** and Alexandra Uma. 2021. We need [to](https://doi.org/10.18653/v1/2021.bppf-1.3) consider

**670** disagreement in evaluation. In _Proceedings_ _of_ _the_

**671** _1st Workshop on Benchmarking:_ _Past, Present and_

**672** _Future_, pages 15–21, Online. Association for Com
**673** putational Linguistics.

**674** Nitay Calderon, Roi Reichart, and Rotem Dror. 2025.

**675** The alternative [annotator](https://arxiv.org/abs/2501.10970) test for llm-as-a-judge:

**676** How to statistically [justify](https://arxiv.org/abs/2501.10970) replacing human anno
**677** [tators with llms.](https://arxiv.org/abs/2501.10970) _Preprint_, arXiv:2501.10970.

**678** Georgios Chochlakis, Alexandros Potamianos, Kristina

**679** Lerman, and Shrikanth Narayanan. 2024. [The strong](https://arxiv.org/abs/2403.17125)

pull of prior knowledge [in](https://arxiv.org/abs/2403.17125) large language models **680**
and its impact on [emotion](https://arxiv.org/abs/2403.17125) recognition. _Preprint_, **681**
arXiv:2403.17125. **682**

Georgios Chochlakis, Alexandros Potamianos, Kristina **683**
Lerman, and Shrikanth Narayanan. 2025. [Aggrega-](https://aclanthology.org/2025.naacl-long.284/) **684**
tion artifacts in [subjective](https://aclanthology.org/2025.naacl-long.284/) tasks collapse large lan- **685**
[guage models’ posteriors.](https://aclanthology.org/2025.naacl-long.284/) In _Proceedings of the 2025_ **686**
_Conference of the Nations of the Americas Chapter of_ **687**
_the Association for Computational Linguistics:_ _Hu-_ **688**
_man_ _Language_ _Technologies_ _(Volume_ _1:_ _Long_ _Pa-_ **689**
_pers)_, pages 5513–5528, Albuquerque, New Mexico. **690**
Association for Computational Linguistics. **691**

Ganqu Cui, Lifan Yuan, Ning Ding, Guanming **692**
Yao, Bingxiang He, Wei Zhu, Yuan Ni, Guotong **693**
Xie, Ruobing Xie, Yankai Lin, Zhiyuan Liu, and **694**
Maosong Sun. 2024. [Ultrafeedback:](https://arxiv.org/abs/2310.01377) Boosting lan- **695**
guage models with scaled ai feedback. _Preprint_, **696**
arXiv:2310.01377. **697**

[DeepSeek-AI.](https://arxiv.org/abs/2501.12948) 2025. Deepseek-r1: [Incentivizing](https://arxiv.org/abs/2501.12948) rea- **698**
[soning capability in llms via reinforcement learning.](https://arxiv.org/abs/2501.12948) **699**
_Preprint_, arXiv:2501.12948. **700**

Dorottya Demszky, Dana Movshovitz-Attias, Jeongwoo **701**
Ko, Alan Cowen, Gaurav Nemade, and Sujith Ravi. **702**
2020\. GoEmotions: [A dataset of fine-grained emo-](https://doi.org/10.18653/v1/2020.acl-main.372) **703**
[tions.](https://doi.org/10.18653/v1/2020.acl-main.372) In _Proceedings of the 58th Annual Meeting of_ **704**
_the Association for Computational Linguistics_, pages **705**
4040–4054, Online. Association for Computational **706**
Linguistics. **707**

Esin Durmus, Karina Nguyen, Thomas I. Liao, **708**
Nicholas Schiefer, Amanda Askell, Anton Bakhtin, **709**
Carol Chen, Zac Hatfield-Dodds, Danny Hernan- **710**
dez, Nicholas Joseph, Liane Lovitt, Sam McCan- **711**
dlish, Orowa Sikder, Alex Tamkin, Janel Thamkul, **712**
Jared Kaplan, Jack Clark, and Deep Ganguli. 2024. **713**
Towards measuring the representation of subjec- **714**
[tive global opinions in language models.](https://arxiv.org/abs/2306.16388) _Preprint_, **715**
arXiv:2306.16388. **716**

[Eve Fleisig, Rediet Abebe, and Dan Klein. 2023.](https://doi.org/10.18653/v1/2023.emnlp-main.415) [When](https://doi.org/10.18653/v1/2023.emnlp-main.415) **717**
the majority is wrong: [Modeling annotator disagree-](https://doi.org/10.18653/v1/2023.emnlp-main.415) **718**
[ment for subjective tasks.](https://doi.org/10.18653/v1/2023.emnlp-main.415) In _Proceedings of the 2023_ **719**
_Conference_ _on_ _Empirical_ _Methods_ _in_ _Natural_ _Lan-_ **720**
_guage Processing_, pages 6715–6726, Singapore. As- **721**
sociation for Computational Linguistics. **722**

Tommaso Fornaciari, Alexandra Uma, Silviu Paun, Bar- **723**
bara Plank, Dirk Hovy, and Massimo Poesio. 2021. **724**
Beyond black & white: [Leveraging](https://doi.org/10.18653/v1/2021.naacl-main.204) annotator dis- **725**
[agreement via soft-label multi-task learning.](https://doi.org/10.18653/v1/2021.naacl-main.204) In _Pro-_ **726**
_ceedings of the 2021 Conference of the North Amer-_ **727**
_ican Chapter of the Association for Computational_ **728**
_Linguistics:_ _Human Language Technologies_, pages **729**
2591–2597, Online. Association for Computational **730**
Linguistics. **731**

Lukas M Fuchs, Yu Fan, and Christian von Scheve. **732**
2021\. Value differences between refugees and ger- **733**
man citizens: insights from a representative survey. **734**
_International Migration_, 59(5):59–81. **735**

9

**736** Salvatore Giorgi, Tingting Liu, Ankit Aich, Kelsey Jane

**737** Isman, Garrick Sherman, Zachary Fried, João Sedoc,

**738** Lyle Ungar, and Brenda Curtis. 2024. [Modeling hu-](https://doi.org/10.18653/v1/2024.findings-emnlp.420)

**739** [man subjectivity in LLMs using explicit and implicit](https://doi.org/10.18653/v1/2024.findings-emnlp.420)

**740** [human factors in personas.](https://doi.org/10.18653/v1/2024.findings-emnlp.420) In _Findings of the Associ-_

**741** _ation for Computational Linguistics:_ _EMNLP 2024_,

**742** pages 7174–7188, Miami, Florida, USA. Association

**743** for Computational Linguistics.

**744** Igor Grossmann, Matthew Feinberg, Dawn C Parker,

**745** Nicholas A Christakis, Philip E Tetlock, and

**746** William A Cunningham. 2023. Ai and [the](https://doi.org/10.1126/science.adi1778) trans
**747** formation of [social](https://doi.org/10.1126/science.adi1778) science research. _Science_,

**748** 380(6650):1108–1109.

**749** Pengcheng He, Jianfeng Gao, and Weizhu Chen. 2023.

**750** [Debertav3: Improving deberta using electra-style pre-](https://arxiv.org/abs/2111.09543)

**751** [training with gradient-disentangled embedding shar-](https://arxiv.org/abs/2111.09543)

**752** [ing.](https://arxiv.org/abs/2111.09543) _Preprint_, arXiv:2111.09543.

**753** Xingwei He, Zhenghao Lin, Yeyun Gong, A-Long Jin,

**754** Hang Zhang, Chen Lin, Jian Jiao, Siu Ming Yiu, Nan

**755** Duan, and Weizhu Chen. 2024a. [Annollm:](https://arxiv.org/abs/2303.16854) Making

**756** large language models [to](https://arxiv.org/abs/2303.16854) be better crowdsourced

**757** [annotators.](https://arxiv.org/abs/2303.16854) _Preprint_, arXiv:2303.16854.

**758** Zeyu He, Chieh-Yang Huang, Chien-Kuang Cornelia

**759** Ding, Shaurya Rohatgi, and Ting-Hao Kenneth

**760** Huang. 2024b. If in a [crowdsourced](https://doi.org/10.1145/3613904.3642834) data annota
**761** tion [pipeline,](https://doi.org/10.1145/3613904.3642834) a gpt-4. In _Proceedings_ _of_ _the_ _2024_

**762** _CHI_ _Conference_ _on_ _Human_ _Factors_ _in_ _Computing_

**763** _Systems_, CHI ’24, New York, NY, USA. Association

**764** for Computing Machinery.

**765** Julia Hirschberg, Jackson Liscombe, and Jennifer Ven
**766** ditti. 2003. Experiments in emotional speech. In

**767** _ISCA & IEEE Workshop on Spontaneous Speech Pro-_

**768** _cessing and Recognition_, pages 1–7.

**769** Dirk Hovy, Taylor Berg-Kirkpatrick, Ashish Vaswani,

**770** and Eduard Hovy. 2013. Learning [whom](https://aclanthology.org/N13-1132/) to trust

**771** [with MACE.](https://aclanthology.org/N13-1132/) In _Proceedings of the 2013 Conference_

**772** _of_ _the_ _North_ _American_ _Chapter_ _of_ _the_ _Association_

**773** _for_ _Computational_ _Linguistics:_ _Human_ _Language_

**774** _Technologies_, pages 1120–1130, Atlanta, Georgia.

**775** Association for Computational Linguistics.

**776** [Tiancheng Hu and Nigel Collier. 2024.](https://doi.org/10.18653/v1/2024.acl-long.554) [Quantifying the](https://doi.org/10.18653/v1/2024.acl-long.554)

**777** [persona effect in LLM simulations.](https://doi.org/10.18653/v1/2024.acl-long.554) In _Proceedings_

**778** _of_ _the_ _62nd_ _Annual_ _Meeting_ _of_ _the_ _Association_ _for_

**779** _Computational Linguistics (Volume 1:_ _Long Papers)_,

**780** pages 10289–10307, Bangkok, Thailand. Association

**781** for Computational Linguistics.

**782** Nan-Jiang Jiang and Marie-Catherine de Marneffe.

**783** 2022. [Investigating reasons for disagreement in natu-](https://doi.org/10.1162/tacl_a_00523)

**784** [ral language inference.](https://doi.org/10.1162/tacl_a_00523) _Transactions of the Associa-_

**785** _tion for Computational Linguistics_, 10:1357–1374.

**786** [Shapeng Jiang, Lijia Wei, and Chen Zhang. 2025.](https://arxiv.org/abs/2411.01582) [Don-](https://arxiv.org/abs/2411.01582)

**787** [ald trumps in the virtual polls:](https://arxiv.org/abs/2411.01582) Simulating and pre
**788** dicting public opinions [in](https://arxiv.org/abs/2411.01582) surveys using large lan
**789** [guage models.](https://arxiv.org/abs/2411.01582) _Preprint_, arXiv:2411.01582.

**790** Rabimba Karanjai, Boris Shor, Amanda Austin, Ryan

**791** Kennedy, Yang Lu, Lei Xu, and Weidong Shi.

2025. [Synthesizing public opinions with llms:](https://arxiv.org/abs/2504.00241) Role **792**
      creation, impacts, and [the](https://arxiv.org/abs/2504.00241) future to edemorcacy. **793**
      _Preprint_, arXiv:2504.00241. **794**

Brendan Kennedy, Mohammad Atari, **795**
Aida Mostafazadeh Davani, Leigh Yeh, Ali **796**
Omrani, Yehsong Kim, Kris Coombs, Shreya **797**
Havaldar, Gwenyth Portillo-Wightman, Elaine **798**
Gonzalez, and 1 others. 2018. [The gab hate corpus:](https://doi.org/10.31234/osf.io/hqjxn) **799**
[A collection of 27k posts annotated for hate speech.](https://doi.org/10.31234/osf.io/hqjxn) **800**
_PsyArXiv. July_, 18. **801**

Nathan Lambert, Jacob Morrison, Valentina Pyatkin, **802**
Shengyi Huang, Hamish Ivison, Faeze Brahman, **803**
Lester James V. Miranda, Alisa Liu, Nouha Dziri, **804**
Shane Lyu, Yuling Gu, Saumya Malik, Victoria **805**
Graf, Jena D. Hwang, Jiangjiang Yang, Ronan Le **806**
Bras, Oyvind Tafjord, Chris Wilhelm, Luca Sol- **807**
daini, and 4 others. 2025. Tulu 3: [Pushing](https://arxiv.org/abs/2411.15124) fron- **808**
[tiers in open language model post-training.](https://arxiv.org/abs/2411.15124) _Preprint_, **809**
arXiv:2411.15124. **810**

Harrison Lee, Samrat Phatale, Hassan Mansoor, Thomas **811**
Mesnard, Johan Ferret, Kellie Lu, Colton Bishop, **812**
Ethan Hall, Victor Carbune, Abhinav Rastogi, and **813**
Sushant Prakash. 2024. Rlaif vs. [rlhf:](https://arxiv.org/abs/2309.00267) Scaling re- **814**
[inforcement learning from human feedback with ai](https://arxiv.org/abs/2309.00267) **815**
[feedback.](https://arxiv.org/abs/2309.00267) _Preprint_, arXiv:2309.00267. **816**

Elisa Leonardelli, Gavin Abercrombie, Dina Almanea, **817**
Valerio Basile, Tommaso Fornaciari, Barbara Plank, **818**
Verena Rieser, Alexandra Uma, and Massimo Poe- **819**
sio. 2023. SemEval-2023 [task](https://doi.org/10.18653/v1/2023.semeval-1.314) 11: Learning with **820**
[disagreements](https://doi.org/10.18653/v1/2023.semeval-1.314) (LeWiDi). In _Proceedings_ _of_ _the_ **821**
_17th International Workshop on Semantic Evaluation_ **822**
_(SemEval-2023)_, pages 2304–2318, Toronto, Canada. **823**
Association for Computational Linguistics. **824**

Ryan Liu, Jiayi Geng, Addison J. Wu, Ilia Sucholut- **825**
sky, Tania Lombrozo, and Thomas L. Griffiths. 2024. **826**
[Mind your step (by step):](https://arxiv.org/abs/2410.21333) Chain-of-thought can re- **827**
duce performance on [tasks](https://arxiv.org/abs/2410.21333) where thinking makes **828**
[humans worse.](https://arxiv.org/abs/2410.21333) _Preprint_, arXiv:2410.21333. **829**

Clara Meister, Mario Giulianelli, and Tiago Pimentel. **830**
2024a. [Towards a similarity-adjusted surprisal the-](https://doi.org/10.18653/v1/2024.emnlp-main.921) **831**
[ory.](https://doi.org/10.18653/v1/2024.emnlp-main.921) In _Proceedings of the 2024 Conference on Em-_ **832**
_pirical_ _Methods_ _in_ _Natural_ _Language_ _Processing_, **833**
pages 16485–16498, Miami, Florida, USA. Associa- **834**
tion for Computational Linguistics. **835**

Nicole Meister, Carlos Guestrin, and Tatsunori **836**
Hashimoto. 2024b. [Benchmarking](https://arxiv.org/abs/2411.05403) distributional **837**
alignment of [large](https://arxiv.org/abs/2411.05403) language models. _Preprint_, **838**
arXiv:2411.05403. **839**

[Cade Metz and Karen Weise. 2025.](https://www.nytimes.com/2025/05/05/technology/ai-hallucinations-chatgpt-google.html) [A.i. is getting more](https://www.nytimes.com/2025/05/05/technology/ai-hallucinations-chatgpt-google.html) **840**
powerful, but its [hallucinations](https://www.nytimes.com/2025/05/05/technology/ai-hallucinations-chatgpt-google.html) are getting worse. **841**
_The New York Times_ . Accessed: 2025-05-10. **842**

Rada Mihalcea and Hugo Liu. 2006. A corpus-based **843**
approach to finding happiness. In _AAAI Spring Sym-_ **844**
_posium:_ _Computational_ _Approaches_ _to_ _Analyzing_ **845**
_Weblogs_, pages 139–144. **846**

10

**847** Aida Mostafazadeh Davani, Mark Díaz, and Vinodku
**848** mar Prabhakaran. 2022. [Dealing with disagreements:](https://doi.org/10.1162/tacl_a_00449)

**849** [Looking beyond the majority vote in subjective an-](https://doi.org/10.1162/tacl_a_00449)

**850** [notations.](https://doi.org/10.1162/tacl_a_00449) _Transactions of the Association for Com-_

**851** _putational Linguistics_, 10:92–110.

**852** Niklas Muennighoff, Zitong Yang, Weijia Shi, Xi
**853** ang Lisa Li, Li Fei-Fei, Hannaneh Hajishirzi, Luke

**854** Zettlemoyer, Percy Liang, Emmanuel Candès, and

**855** Tatsunori Hashimoto. 2025. s1: [Simple](https://arxiv.org/abs/2501.19393) test-time

**856** [scaling.](https://arxiv.org/abs/2501.19393) _Preprint_, arXiv:2501.19393.

**857** Jingwei Ni, Tobias Schimanski, Meihong Lin, Mrin
**858** maya Sachan, Elliott Ash, and Markus Leippold.

**859** 2025. DIRAS: Efficient [LLM](https://aclanthology.org/2025.naacl-long.271/) annotation of doc
**860** [ument relevance for retrieval augmented generation.](https://aclanthology.org/2025.naacl-long.271/)

**861** In _Proceedings_ _of_ _the_ _2025_ _Conference_ _of_ _the_ _Na-_

**862** _tions of the Americas Chapter of the Association for_

**863** _Computational Linguistics:_ _Human Language Tech-_

**864** _nologies (Volume 1:_ _Long Papers)_, pages 5238–5258,

**865** Albuquerque, New Mexico. Association for Compu
**866** tational Linguistics.

**867** Jingwei Ni, Minjing Shi, Dominik Stammbach, Mrin
**868** maya Sachan, Elliott Ash, and Markus Leippold.

**869** 2024. [AFaCTA: Assisting the annotation of factual](https://doi.org/10.18653/v1/2024.acl-long.104)

**870** claim detection with [reliable](https://doi.org/10.18653/v1/2024.acl-long.104) LLM annotators. In

**871** _Proceedings of the 62nd Annual Meeting of the As-_

**872** _sociation for Computational Linguistics (Volume 1:_

**873** _Long Papers)_, pages 1890–1912, Bangkok, Thailand.

**874** Association for Computational Linguistics.

**875** [Loran](https://doi.org/10.1086/596306) F. Nordgren and Ap Dijksterhuis. 2009. [The](https://doi.org/10.1086/596306)

**876** devil is in the [deliberation:](https://doi.org/10.1086/596306) Thinking too much re
**877** [duces preference consistency.](https://doi.org/10.1086/596306) _Journal of Consumer_

**878** _Research_, 36(1):39–46.

**879** Matthias Orlikowski, Jiaxin Pei, Paul Röttger, Philipp

**880** Cimiano, David Jurgens, and Dirk Hovy. 2025. [Be-](https://arxiv.org/abs/2502.20897)

**881** [yond demographics: Fine-tuning large language mod-](https://arxiv.org/abs/2502.20897)

**882** [els to predict individuals’ subjective text perceptions.](https://arxiv.org/abs/2502.20897)

**883** _Preprint_, arXiv:2502.20897.

**884** Long Ouyang, Jeff Wu, Xu Jiang, Diogo Almeida, Car
**885** roll L. Wainwright, Pamela Mishkin, Chong Zhang,

**886** Sandhini Agarwal, Katarina Slama, Alex Ray, John

**887** Schulman, Jacob Hilton, Fraser Kelton, Luke Miller,

**888** Maddie Simens, Amanda Askell, Peter Welinder,

**889** Paul Christiano, Jan Leike, and Ryan Lowe. 2022.

**890** [Training language models to follow instructions with](https://arxiv.org/abs/2203.02155)

**891** [human feedback.](https://arxiv.org/abs/2203.02155) _Preprint_, arXiv:2203.02155.

**892** [Cecilia Ovesdotter Alm. 2011.](https://aclanthology.org/P11-2019/) [Subjective natural lan-](https://aclanthology.org/P11-2019/)

**893** guage problems: [Motivations, applications, charac-](https://aclanthology.org/P11-2019/)

**894** [terizations, and implications.](https://aclanthology.org/P11-2019/) In _Proceedings of the_

**895** _49th Annual Meeting of the Association for Compu-_

**896** _tational Linguistics:_ _Human Language Technologies_,

**897** pages 107–112, Portland, Oregon, USA. Association

**898** for Computational Linguistics.

**899** Nicholas Pangakis, Samuel Wolken, and Neil Fasching.

**900** 2023a. [Automated annotation with generative ai re-](https://api.semanticscholar.org/CorpusID:259000016)

**901** [quires validation.](https://api.semanticscholar.org/CorpusID:259000016) _ArXiv_, abs/2306.00176.

**902** Nicholas Pangakis, Samuel Wolken, and Neil Fasching.

**903** 2023b. Automated [annotation](https://arxiv.org/abs/2306.00176) with generative ai

**904** [requires validation.](https://arxiv.org/abs/2306.00176) _Preprint_, arXiv:2306.00176.

Karl Pearson. 1895. Note on regression and inheritance **905**
in the case of two parents. _Proceedings of the Royal_ **906**
_Society of London_, 58:240–242. **907**

[Barbara Plank. 2022.](https://doi.org/10.18653/v1/2022.emnlp-main.731) [The “problem” of human label](https://doi.org/10.18653/v1/2022.emnlp-main.731) **908**
variation: On ground [truth](https://doi.org/10.18653/v1/2022.emnlp-main.731) in data, modeling and **909**
[evaluation.](https://doi.org/10.18653/v1/2022.emnlp-main.731) In _Proceedings of the 2022 Conference_ **910**
_on Empirical Methods in Natural Language Process-_ **911**
_ing_, pages 10671–10682, Abu Dhabi, United Arab **912**
Emirates. Association for Computational Linguistics. **913**

Barbara Plank, Dirk Hovy, and Anders Søgaard. 2014. **914**
Linguistically [debatable](https://doi.org/10.3115/v1/P14-2083) or just plain wrong? In **915**
_Proceedings of the 52nd Annual Meeting of the As-_ **916**
_sociation for Computational Linguistics (Volume 2:_ **917**
_Short Papers)_, pages 507–511, Baltimore, Maryland. **918**
Association for Computational Linguistics. **919**

[Maja](https://doi.org/10.18653/v1/2021.conll-1.18) Popovi´c. 2021. Agree to [disagree:](https://doi.org/10.18653/v1/2021.conll-1.18) Analysis of **920**
[inter-annotator disagreements in human evaluation](https://doi.org/10.18653/v1/2021.conll-1.18) **921**
of machine [translation](https://doi.org/10.18653/v1/2021.conll-1.18) output. In _Proceedings_ _of_ **922**
_the 25th Conference on Computational Natural Lan-_ **923**
_guage Learning_, pages 234–243, Online. Association **924**
for Computational Linguistics. **925**

Marta Sabou, Kalina Bontcheva, Leon Derczynski, **926**
and Arno Scharl. 2014. Corpus annotation through **927**
crowdsourcing: Towards best practice guidelines. In **928**
_Proceedings of the Ninth International Conference_ **929**
_on Language Resources and Evaluation (LREC’14)_, **930**
Reykjavik, Iceland. European Language Resources **931**
Association (ELRA). **932**

Marta Sandri, Elisa Leonardelli, Sara Tonelli, and Elis- **933**
abetta Jezek. 2023. Why don‘t [you](https://doi.org/10.18653/v1/2023.eacl-main.178) do it right? **934**
analysing annotators’ [disagreement](https://doi.org/10.18653/v1/2023.eacl-main.178) in subjective **935**
[tasks.](https://doi.org/10.18653/v1/2023.eacl-main.178) In _Proceedings_ _of_ _the_ _17th_ _Conference_ _of_ **936**
_the European Chapter of the Association for Compu-_ **937**
_tational Linguistics_, pages 2428–2441, Dubrovnik, **938**
Croatia. Association for Computational Linguistics. **939**

Shibani Santurkar, Esin Durmus, Faisal Ladhak, Cinoo **940**
Lee, Percy Liang, and Tatsunori Hashimoto. 2023. **941**
Whose opinions do [language](https://proceedings.mlr.press/v202/santurkar23a.html) models reflect? In **942**
_Proceedings_ _of_ _the_ _40th_ _International_ _Conference_ **943**
_on Machine Learning_, volume 202 of _Proceedings_ **944**
_of Machine Learning Research_, pages 29971–30004. **945**
PMLR. **946**

Sebastin Santy, Jenny Liang, Ronan Le Bras, Katharina **947**
Reinecke, and Maarten Sap. 2023. [NLPositionality:](https://doi.org/10.18653/v1/2023.acl-long.505) **948**
[Characterizing design biases of datasets and models.](https://doi.org/10.18653/v1/2023.acl-long.505) **949**
In _Proceedings_ _of_ _the_ _61st_ _Annual_ _Meeting_ _of_ _the_ **950**
_Association for Computational Linguistics (Volume_ **951**
_1:_ _Long Papers)_, pages 9080–9102, Toronto, Canada. **952**
Association for Computational Linguistics. **953**

Rion Snow, Brendan O’Connor, Daniel Jurafsky, and **954**
Andrew Ng. 2008. [Cheap and fast – but is it good?](https://aclanthology.org/D08-1027/) **955**
evaluating non-expert [annotations](https://aclanthology.org/D08-1027/) for natural lan- **956**
[guage tasks.](https://aclanthology.org/D08-1027/) In _Proceedings of the 2008 Conference_ **957**
_on Empirical Methods in Natural Language Process-_ **958**
_ing_, pages 254–263, Honolulu, Hawaii. Association **959**
for Computational Linguistics. **960**

11

**961** Taylor Sorensen, Jared Moore, Jillian Fisher,

**962** Mitchell Gordon, Niloofar Mireshghallah, Christo
**963** pher Michael Rytting, Andre Ye, Liwei Jiang,

**964** Ximing Lu, Nouha Dziri, Tim Althoff, and Yejin

**965** Choi. 2024. Position: a roadmap to pluralistic

**966** alignment. In _Proceedings of the 41st International_

**967** _Conference_ _on_ _Machine_ _Learning_, ICML’24.

**968** JMLR.org.

**969** Zhen Tan, Dawei Li, Song Wang, Alimohammad

**970** Beigi, Bohan Jiang, Amrita Bhattacharjee, Man
**971** sooreh Karami, Jundong Li, Lu Cheng, and Huan Liu.

**972** 2024. [Large language models for data annotation and](https://doi.org/10.18653/v1/2024.emnlp-main.54)

**973** [synthesis:](https://doi.org/10.18653/v1/2024.emnlp-main.54) A survey. In _Proceedings of the 2024 Con-_

**974** _ference on Empirical Methods in Natural Language_

**975** _Processing_, pages 930–957, Miami, Florida, USA.

**976** Association for Computational Linguistics.

**977** Katherine Tian, Eric Mitchell, Allan Zhou, Archit

**978** Sharma, Rafael Rafailov, Huaxiu Yao, Chelsea Finn,

**979** and Christopher D. Manning. 2023. [Just ask for cali-](https://arxiv.org/abs/2305.14975)

**980** bration: [Strategies for eliciting calibrated confidence](https://arxiv.org/abs/2305.14975)

**981** [scores from language models fine-tuned with human](https://arxiv.org/abs/2305.14975)

**982** [feedback.](https://arxiv.org/abs/2305.14975) _Preprint_, arXiv:2305.14975.

**983** [Petter Törnberg. 2024.](https://api.semanticscholar.org/CorpusID:267547980) [Best practices for text annotation](https://api.semanticscholar.org/CorpusID:267547980)

**984** [with large language models.](https://api.semanticscholar.org/CorpusID:267547980) _ArXiv_, abs/2402.05129.

**985** Miles Turpin, Julian Michael, Ethan Perez, and

**986** Samuel R. Bowman. 2023. [Language](https://arxiv.org/abs/2305.04388) models

**987** don’t always say what [they](https://arxiv.org/abs/2305.04388) think: Unfaithful ex
**988** [planations in chain-of-thought prompting.](https://arxiv.org/abs/2305.04388) _Preprint_,

**989** arXiv:2305.04388.

**990** [Petter](https://arxiv.org/abs/2304.06588) Törnberg. 2023. Chatgpt-4 [outperforms](https://arxiv.org/abs/2304.06588) ex
**991** [perts and crowd workers in annotating political twit-](https://arxiv.org/abs/2304.06588)

**992** ter messages with zero-shot learning. _Preprint_,

**993** arXiv:2304.06588.

**994** Alexandra Uma, Tommaso Fornaciari, Dirk Hovy, Sil
**995** viu Paun, Barbara Plank, and Massimo Poesio. 2021.

**996** [Learning from disagreement:](https://api.semanticscholar.org/CorpusID:245589751) A survey. _J. Artif. In-_

**997** _tell. Res._, 72:1385–1470.

**998** Zhaoyang Wang, Weilei He, Zhiyuan Liang, Xuchao

**999** Zhang, Chetan Bansal, Ying Wei, Weitong Zhang,

**1000** and Huaxiu Yao. 2025a. Cream: [Consistency](https://arxiv.org/abs/2410.12735) reg
**1001** [ularized self-rewarding language models.](https://arxiv.org/abs/2410.12735) _Preprint_,

**1002** arXiv:2410.12735.

**1003** Zhilin Wang, Alexander Bukharin, Olivier Delal
**1004** leau, Daniel Egert, Gerald Shen, Jiaqi Zeng, Olek
**1005** sii Kuchaiev, and Yi Dong. 2025b. [Helpsteer2-](https://arxiv.org/abs/2410.01257)

**1006** preference: [Complementing ratings with preferences.](https://arxiv.org/abs/2410.01257)

**1007** _Preprint_, arXiv:2410.01257.

**1008** Benjamin Warner, Antoine Chaffin, Benjamin Clavié,

**1009** Orion Weller, Oskar Hallström, Said Taghadouini,

**1010** Alexis Gallagher, Raja Biswas, Faisal Ladhak, Tom

**1011** Aarsen, Nathan Cooper, Griffin Adams, Jeremy

**1012** Howard, and Iacopo Poli. 2024. [Smarter,](https://arxiv.org/abs/2412.13663) better,

**1013** faster, longer: A modern bidirectional encoder for

**1014** [fast, memory efficient, and long context finetuning](https://arxiv.org/abs/2412.13663)

**1015** [and inference.](https://arxiv.org/abs/2412.13663) _Preprint_, arXiv:2412.13663.

[William Warner and Julia Hirschberg. 2012.](https://aclanthology.org/W12-2103/) [Detecting](https://aclanthology.org/W12-2103/) **1016**
[hate speech on the world wide web.](https://aclanthology.org/W12-2103/) In _Proceedings_ **1017**
_of the Second Workshop on Language in Social Me-_ **1018**
_dia_, pages 19–26, Montréal, Canada. Association for **1019**
Computational Linguistics. **1020**

[Zeerak Waseem. 2016.](https://doi.org/10.18653/v1/W16-5618) [Are you a racist or am I seeing](https://doi.org/10.18653/v1/W16-5618) **1021**
things? [annotator influence on hate speech detection](https://doi.org/10.18653/v1/W16-5618) **1022**
[on Twitter.](https://doi.org/10.18653/v1/W16-5618) In _Proceedings of the First Workshop on_ **1023**
_NLP and Computational Social Science_, pages 138– **1024**
142, Austin, Texas. Association for Computational **1025**
Linguistics. **1026**

Jason Wei, Nguyen Karina, Hyung Won Chung, **1027**
Yunxin Joy Jiao, Spencer Papay, Amelia Glaese, **1028**
John Schulman, and William Fedus. 2024. [Mea-](https://arxiv.org/abs/2411.04368) **1029**
[suring short-form factuality in large language models.](https://arxiv.org/abs/2411.04368) **1030**
_Preprint_, arXiv:2411.04368. **1031**

Jason Wei, Xuezhi Wang, Dale Schuurmans, Maarten **1032**
Bosma, Brian Ichter, Fei Xia, Ed Chi, Quoc Le, and **1033**
Denny Zhou. 2023. [Chain-of-thought prompting elic-](https://arxiv.org/abs/2201.11903) **1034**
its reasoning in [large](https://arxiv.org/abs/2201.11903) language models. _Preprint_, **1035**
arXiv:2201.11903. **1036**

Janyce Wiebe, Theresa Wilson, Rebecca Bruce, **1037**
Matthew Bell, and Melanie Martin. 2004. [Learn-](https://doi.org/10.1162/0891201041850885) **1038**
[ing subjective language.](https://doi.org/10.1162/0891201041850885) _Computational Linguistics_, **1039**
30(3):277–308. **1040**

[Frank](https://doi.org/10.1007/978-1-4612-4380-9_16) Wilcoxon. 1992. _Individual_ _[Comparisons](https://doi.org/10.1007/978-1-4612-4380-9_16)_ _by_ **1041**
_Ranking_ _Methods_, pages 196–202. Springer New **1042**
York, New York, NY. **1043**

Michael JQ Zhang, Zhilin Wang, Jena D. Hwang, **1044**
Yi Dong, Olivier Delalleau, Yejin Choi, Eunsol Choi, **1045**
Xiang Ren, and Valentina Pyatkin. 2024. [Diverging](https://arxiv.org/abs/2410.14632) **1046**
preferences: When do [annotators](https://arxiv.org/abs/2410.14632) disagree and do **1047**
[models know?](https://arxiv.org/abs/2410.14632) _Preprint_, arXiv:2410.14632. **1048**

Lianmin Zheng, Wei-Lin Chiang, Ying Sheng, Siyuan **1049**
Zhuang, Zhanghao Wu, Yonghao Zhuang, Zi Lin, **1050**
Zhuohan Li, Dacheng Li, Eric P. Xing, Hao Zhang, **1051**
Joseph E. Gonzalez, and Ion Stoica. 2023. [Judg-](https://arxiv.org/abs/2306.05685) **1052**
[ing llm-as-a-judge with mt-bench and chatbot arena.](https://arxiv.org/abs/2306.05685) **1053**
_Preprint_, arXiv:2306.05685. **1054**

Xin Zhou, Yiwen Guo, Ruotian Ma, Tao Gui, Qi Zhang, **1055**
and Xuanjing Huang. 2025. [Self-consistency of the](https://arxiv.org/abs/2502.08922) **1056**
[internal reward models improves self-rewarding lan-](https://arxiv.org/abs/2502.08922) **1057**
[guage models.](https://arxiv.org/abs/2502.08922) _Preprint_, arXiv:2502.08922. **1058**

Caleb Ziems, William Held, Omar Shaikh, Jiaao Chen, **1059**
Zhehao Zhang, and Diyi Yang. 2024. [Can large lan-](https://doi.org/10.1162/coli_a_00502) **1060**
guage models transform computational social sci- **1061**
[ence?](https://doi.org/10.1162/coli_a_00502) _Computational Linguistics_, 50(1):237–291. **1062**

**A** **Dataset Preparation** **1063**

For all datasets, we only use the data points with at **1064**
least 4 annotators for both training and evaluation **1065**
to ensure annotation quality. Data points with 3 **1066**
annotations may have one annotator disagree with **1067**
the others, and the disagreement might be caused **1068**
by random annotation error (e.g., a wrong click). **1069**

12

**1070** As shown by (Sandri et al., 2023), 2 annotators

**1071** making random mistake might be 100 times less

**1072** likely than 1 annotator doing that.

**1073** After this filtering, we randomly select 2,000

**1074** data points from the 3,330 Gab Hate Corpus sam
**1075** ples, 2,000 data points from the 20,014 GoEmo
**1076** tions samples, and 1,250 data points from the 2,467

**1077** HelpSteer2 samples as training data; and 1K data
**1078** points for Random subsets for testing. The size of

**1079** training set is strategically picked so that there are

**1080** enough annotations with high human annotation

**1081** variance to form the HighVar subsets. HelpSteer2

**1082** has a smaller training set because it has less data
**1083** points with at least 4 annotations. Therefore, we

**1084** shrink its training sets’ size to ensure the size of

**1085** evaluation sets.

**1086** The distributions of human annotation _pd_ of each

**1087** dataset are presented in Fig. 2.

**1088** **B** **Prompts**

**1089** Here we use Gab Hate Corpus prompts to showcase

**1090** our prompt design. Tasks for other datasets can be

**1091** found in our Github repository.

**1092** One example prompt for Gab Hate Corpus is

**1093** illustrated bellow, with verbalized distribution and

**1094** w/o few-shot steering. It is used for RLVR LLMs

**1095** and for RLHF w/o reasoning, since no reasoning

**1096** is required in output format. In the instruction part,

**1097** the model is guided to consider potential disagree
**1098** ment.

and consider its content in relation to the three aspects
of hate speech listed above.

- Assess Agreement: Human annotators may have high
  disagreement if the post contains ambiguous language
  or context, or if it is likely to be interpreted differently
  based on subjective views about the severity or nature
  of hate speech. They may have low disagreement if the
  post clearly falls into one or more of the hate speech
  categories or is obviously not hate speech.

- Context Sensitivity: Consider the cultural, social, and
  linguistic context that may influence the interpretation
  of the post.

Output Format:

\[Percentage\]: a floating-point number indicating the percentages of annotators who classify the post as hate
speech, in a squared bracket, e.g., [0.3]. Omit explanations and only give the percentage.
Here is the post: post

**1100**

For sampling-based distribution, the objective **1101**
and output format changes to follows, where the **1102**
LLM is asked to predict the “most likely” annota- **1103**
tion from human. **1104**

**1108**

For few-shot steering, we add the following in- **1109**
context examples. The few-shot illustrations are **1110**
carefully picked to avoid biasing the output distri- **1111**
bution (Turpin et al., 2023). **1112**

**1105**

When using RLHF LLMs with CoT, we change **1106**
the output format requirements to: **1107**

**1099**

13

**1113**

**1114** **C** **Inference Details**

**1115** **LLMs.** We use the following LLMs—

**1116** RLHF LLMs: Llama-3.1-Tulu-3.1-8B [11] ;

**1117** Qwen2.5-14B-Instruct;

**1118** Qwen2.5-32B-Instruct;

**1119** Llama-3.3-70B-Instruct, and DeepSeek-V3.

**1120** RLVR LLMs: DeepSeek-R1-Distill-Llama-8B;

**1121** DeepSeek-R1-Distill-Qwen-14B;

**1122** DeepSeek-R1-Distill-Qwen-32B;

**1123** DeepSeek-R1-Distill-Llama-70B; and

**1124** DeepSeek-R1.

**1125** **Framework** **and** **Hyperparameters.** For 8B to

**1126** 70B LLMs, we rely on a cluster with 4 GH200

**1127** GPUs for local inference. We use vLLM for fast

**1128** inference. For R1-series RLVR LLMs, we use all

**1129** official recommended settings, including a temper
**1130** ature of 0.6, and always add <think> at the begin
**1131** ning of assistant message. For RLHF LLMs, we

**1132** use temperature 0 for verbalized distribution and

11Llama-3.1-8B-Instruct from Meta refuse classify hate
speeches, so we use Tulu-3.1 which is also based on Llama3.1-8B

0.7 for sampling-based distribution. All other hy- **1133**
perparameters are set to default without restriction **1134**
on generation length. For the 671B LLMs, we use **1135**
DeepSeek API with recommended settings. **1136**

**Computational Cost.** The majority of inference **1137**
cost goes to RLVR LLMs. For the RLVR LLMs **1138**
of 70B, 32B, 14B, and 8B, the inference costs 100, **1139**
40, 20, and 10 GPU hours correspondingly, where **1140**
the majority is spent on sampling-based distribu- **1141**
tion which requires sampling 10 times. For RLHF **1142**
LLMs, especially without CoT, the cost is much **1143**
less. The RLHF LLMs of 70B, 32B, 14B, and **1144**
8B cost 40, 20, 10, 10 GPU hours correspond- **1145**
ingly with the cost of CoT and no-CoT settings **1146**
combined. Note that model loading times are not **1147**
counted into GPU cost. The API cost of DeepSeek- **1148**
R1 and DeepSeek-V3 costs roughly 40 USD in **1149**
total. **1150**

**Packages for Evaluation.** Scipy is used to calcu- **1151**
late Pearson’s Correlations and Wilcoxon Tests. **1152**

**D** **Fine-Tuning Details** **1153**

We use Huggingface to fine-tune and evaluate fine- **1154**
tuned ModernBERT-large and DeBERTa-V3-large. **1155**
We use a learning rate of 5e-5, a weight decay of **1156**
0.01, a batch size of 128, and a epoch number of 5. **1157**
All other hyperparameters are set to default. **1158**

**E** **Results w/o Aggregation** **1159**

Here we present the performance of all LLMs with **1160**
different settings regarding distribution expression, **1161**
steering, and reasoning, which can be used to cal- **1162**
culate all the aggregated results in § 6. Results **1163**
on Random and HighVar subsets are presented in **1164**
Table 5 and Table 6, respectively. **1165**

**F** **Majority Label Prediction** **1166**

In § 6.1, we observe that sampling-based method **1167**
achieves better majority label prediction (F1) than **1168**
verbalized distribution. The prediction of majority **1169**
labels lies outside the scope of this project, so we **1170**
analyze those observations in this appendix sec- **1171**
tion to fully reveal the potential of sampling-based **1172**
methods. We draw the following observations with **1173**
statistical significance. **1174**

1. RLVR LLMs outperform RLHF LLMs, with **1175**
   a win rate 62 _._ 50 _[∗∗]_ % . **1176**

1. RLHF w/ CoT outperforms w/o CoT, with a **1177**
   win rate 62 _._ 50 _[∗∗]_ % . **1178**

14

**1179** 3. Few-shot steering improves the F1 of GHC

**1180** with a rate of 66 _._ 67 _[∗∗]_ %, but decrease the

**1181** HS2, Pos, and Neg where the win rates are

**1182** 6 _._ 67 _[∗∗]_ %, 33 _._ 33 _[∗∗]_ %, and 26 _._ 67 _[∗∗]_ % corre
**1183** spondingly.

**1184** All other trends on F1 do not have statistical

**1185** significance.

**1186** **G** **Per-Dataset Results**

**1187** When comparing RLVR with RLHF LLMs on each

**1188** dataset, the trends are mostly consistent with Ta
**1189** ble 1 row 2 on Random F1 and HighVar DistAlign.

**1190** For Random VarCorr and DistAlgin, we further find

**1191** that following observations with statistical signif
**1192** icance: (1) RLVR underperforms RLHF on HS2

**1193** Random; and (2) RLVR outperforms RLHF on Pos

**1194** Random. The trends in Table 1 summarizes this

**1195** observation, as RLVR vs. RLHF has more mixed

**1196** results on distribution prediction of Random subsets,

**1197** compared to HighVar subsets.

**1198** For CoT vs. w/o CoT on RLHF LLMs, per
**1199** dataset comparison shows that on all datasets, CoT

**1200** either significantly outperforms w/o CoT, or CoT

**1201** slightly underperforms w/o CoT but without statis
**1202** tical significance.

**1203** Furthermore, extending reasoning with RLVR

**1204** LLMs does not lead to significant change to the

**1205** performance on all datasets; while verbalized dis
**1206** tribution constantly performs significantly better

**1207** than sampling-based distribution on all datasets.

Figure 2: Density bars of the Five Random Sets

15

**HelpSteer2** **Gab Hate Corpus** **GE-Positive** **GE-Negative** **GE-Ambiguous**
VarCorr _↑_ DistAlign _↓_ F1 _↑_ VarCorr _↑_ DistAlign _↓_ F1 _↑_ VarCorr _↑_ DistAlign _↓_ F1 _↑_ VarCorr _↑_ DistAlign _↓_ F1 _↑_ VarCorr _↑_ DistAlign _↓_ F1 _↑_

|Col1|Verbalized Distribution|n & w/o Few-shot Steering|Col4|Col5|
|---|---|---|---|---|
|Llama-8B<br>No-CoT<br>0.043<br>0.277<br>0.699<br>CoT<br>0.127<br>0.273<br>0.699<br>R1<br>0.053<br>0.281<br>0.695|0.283<br>0.290<br>0.225<br>0.262<br>0.265<br>0.270<br>0.298<br>0.194<br>0.230|0.109<br>0.357<br>0.504<br>0.121<br>0.269<br>0.631<br>0.186<br>0.240<br>0.547|0.282<br>0.294<br>0.517<br>0.256<br>0.269<br>0.566<br>0.301<br>0.273<br>0.456|0.045<br>0.309<br>0.499<br>0.089<br>0.273<br>0.514<br>0.136<br>0.268<br>0.408|
|Qwen-14B<br>No-CoT<br>0.147<br>0.251<br>0.713<br>CoT<br>0.132<br>0.256<br>0.566<br>R1<br>0.109<br>0.252<br>0.675|0.442<br>0.206<br>0.294<br>0.399<br>0.194<br>0.372<br>0.426<br>0.153<br>0.400|0.175<br>0.228<br>0.637<br>0.194<br>0.222<br>0.647<br>0.256<br>0.214<br>0.670|0.344<br>0.280<br>0.558<br>0.374<br>0.239<br>0.573<br>0.419<br>0.215<br>0.596|0.083<br>0.265<br>0.392<br>0.068<br>0.266<br>0.392<br>0.076<br>0.268<br>0.339|
|Qwen-32B<br>No-CoT<br>0.172<br>0.245<br>0.721<br>CoT<br>0.193<br>0.234<br>0.706<br>R1<br>0.151<br>0.243<br>0.713|0.461<br>0.158<br>0.376<br>0.398<br>0.164<br>0.400<br>0.425<br>0.148<br>0.463|0.195<br>0.220<br>0.552<br>0.210<br>0.214<br>0.594<br>0.262<br>0.209<br>0.625|0.444<br>0.198<br>0.583<br>0.389<br>0.216<br>0.562<br>0.398<br>0.212<br>0.581|0.102<br>0.256<br>0.273<br>0.084<br>0.257<br>0.270<br>0.123<br>0.269<br>0.330|
|Llama-70B<br>No-CoT<br>0.171<br>0.263<br>0.717<br>CoT<br>0.205<br>0.257<br>0.697<br>R1<br>0.180<br>0.230<br>0.722|0.337<br>0.238<br>0.274<br>0.376<br>0.208<br>0.389<br>0.351<br>0.193<br>0.428|0.241<br>0.221<br>0.620<br>0.202<br>0.209<br>0.644<br>0.274<br>0.201<br>0.674|0.409<br>0.245<br>0.579<br>0.379<br>0.234<br>0.567<br>0.332<br>0.234<br>0.595|0.126<br>0.258<br>0.487<br>0.155<br>0.230<br>0.448<br>0.125<br>0.247<br>0.436|
|Deepseek<br>V3-no-CoT<br>0.183<br>0.236<br>0.741<br>V3-CoT<br>0.230<br>0.231<br>0.715<br>R1<br>0.188<br>0.231<br>0.721|0.288<br>0.254<br>0.302<br>0.381<br>0.186<br>0.434<br>0.370<br>0.196<br>0.447|0.194<br>0.220<br>0.721<br>0.233<br>0.216<br>0.675<br>0.204<br>0.209<br>0.649|0.208<br>0.307<br>0.568<br>0.246<br>0.273<br>0.581<br>0.206<br>0.274<br>0.552|0.123<br>0.280<br>0.547<br>0.183<br>0.234<br>0.534<br>0.147<br>0.233<br>0.463|

_Verbalized Distribution + Few-shot Steering_

|No-CoT 0.049 0.293 0.658<br>Llama-8B CoT 0.067 0.297 0.692<br>R1 0.065 0.297 0.676|0.111 0.365 0.147<br>0.215 0.282 0.230<br>0.353 0.186 0.258|0.070 0.325 0.409<br>0.142 0.255 0.526<br>0.234 0.224 0.546|0.052 0.340 0.450<br>0.197 0.276 0.540<br>0.352 0.245 0.456|0.005 0.347 0.489<br>0.123 0.267 0.494<br>0.086 0.279 0.290|
|---|---|---|---|---|
|Qwen-14B<br>No-CoT<br>0.086<br>0.317<br>0.710<br>CoT<br>0.139<br>0.267<br>0.685<br>R1<br>0.114<br>0.255<br>0.674|0.459<br>0.142<br>0.553<br>0.428<br>0.147<br>0.467<br>0.442<br>0.135<br>0.444|0.207<br>0.224<br>0.584<br>0.205<br>0.226<br>0.639<br>0.216<br>0.214<br>0.608|0.371<br>0.226<br>0.557<br>0.387<br>0.224<br>0.580<br>0.402<br>0.214<br>0.593|0.079<br>0.289<br>0.375<br>0.029<br>0.296<br>0.386<br>0.105<br>0.267<br>0.234|
|Qwen-32B<br>No-CoT<br>0.108<br>0.290<br>0.655<br>CoT<br>0.144<br>0.266<br>0.680<br>R1<br>0.066<br>0.298<br>0.558|0.434<br>0.145<br>0.387<br>0.436<br>0.154<br>0.397<br>0.449<br>0.149<br>0.386|0.249<br>0.210<br>0.582<br>0.205<br>0.213<br>0.591<br>0.247<br>0.205<br>0.610|0.288<br>0.241<br>0.555<br>0.394<br>0.230<br>0.567<br>0.365<br>0.223<br>0.570|0.088<br>0.268<br>0.383<br>0.072<br>0.302<br>0.368<br>0.118<br>0.306<br>0.291|
|Llama-70B<br>No-CoT<br>0.083<br>0.299<br>0.684<br>CoT<br>0.182<br>0.297<br>0.687<br>R1<br>0.127<br>0.261<br>0.678|0.431<br>0.166<br>0.378<br>0.413<br>0.164<br>0.467<br>0.433<br>0.161<br>0.447|0.229<br>0.227<br>0.633<br>0.243<br>0.211<br>0.656<br>0.231<br>0.211<br>0.675|0.411<br>0.236<br>0.576<br>0.409<br>0.219<br>0.576<br>0.352<br>0.229<br>0.592|0.083<br>0.310<br>0.471<br>0.132<br>0.248<br>0.490<br>0.118<br>0.274<br>0.411|
|Deepseek<br>V3-no-CoT<br>0.163<br>0.258<br>0.710<br>V3-CoT<br>0.164<br>0.271<br>0.686<br>R1<br>0.128<br>0.291<br>0.455|0.343<br>0.208<br>0.396<br>0.406<br>0.164<br>0.462<br>0.403<br>0.162<br>0.429|0.229<br>0.212<br>0.658<br>0.206<br>0.226<br>0.680<br>0.252<br>0.206<br>0.509|0.085<br>0.331<br>0.490<br>0.220<br>0.300<br>0.566<br>0.322<br>0.257<br>0.479|0.028<br>0.317<br>0.534<br>0.135<br>0.268<br>0.512<br>0.107<br>0.270<br>0.437|

_Sampling-Based Distribution &_ _**w/o**_ _Few-shot Steering_

|No-CoT 0.021 0.423 0.695<br>Llama-8B CoT 0.063 0.440 0.699<br>R1 0.121 0.447 0.697|0.357 0.158 0.398<br>0.215 0.207 0.355<br>0.149 0.233 0.330|0.002 0.286 0.631<br>0.061 0.289 0.631<br>0.169 0.232 0.690|0.097 0.273 0.564<br>0.143 0.308 0.566<br>0.089 0.312 0.586|0.027 0.358 0.521<br>0.004 0.374 0.496<br>0.099 0.292 0.494|
|---|---|---|---|---|
|Qwen-14B<br>No-CoT<br>0.090<br>0.361<br>0.669<br>CoT<br>0.070<br>0.318<br>0.688<br>R1<br>0.124<br>0.282<br>0.705|0.135<br>0.203<br>0.354<br>0.202<br>0.210<br>0.350<br>0.287<br>0.165<br>0.406|0.080<br>0.271<br>0.629<br>0.098<br>0.267<br>0.649<br>0.145<br>0.250<br>0.686|0.047<br>0.332<br>0.567<br>0.083<br>0.324<br>0.593<br>0.234<br>0.281<br>0.595|0.031<br>0.382<br>0.426<br>0.043<br>0.361<br>0.495<br>0.050<br>0.306<br>0.469|
|Qwen-32B<br>No-CoT<br>0.091<br>0.348<br>0.702<br>CoT<br>0.118<br>0.287<br>0.702<br>R1<br>0.073<br>0.294<br>0.759|0.142<br>0.187<br>0.376<br>0.280<br>0.165<br>0.430<br>0.244<br>0.169<br>0.414|0.092<br>0.264<br>0.623<br>0.157<br>0.251<br>0.627<br>0.184<br>0.233<br>0.685|0.124<br>0.297<br>0.590<br>0.208<br>0.290<br>0.589<br>0.192<br>0.285<br>0.607|0.042<br>0.366<br>0.402<br>0.025<br>0.349<br>0.458<br>0.071<br>0.301<br>0.442|
|Llama-70B<br>No-CoT<br>0.024<br>0.412<br>0.673<br>CoT<br>0.124<br>0.357<br>0.693<br>R1<br>0.091<br>0.278<br>0.751|0.074<br>0.263<br>0.298<br>0.146<br>0.216<br>0.337<br>0.175<br>0.208<br>0.344|0.006<br>0.291<br>0.644<br>0.046<br>0.289<br>0.649<br>0.158<br>0.240<br>0.699|0.043<br>0.367<br>0.565<br>0.053<br>0.361<br>0.560<br>0.112<br>0.313<br>0.591|0.014<br>0.393<br>0.513<br>0.030<br>0.355<br>0.516<br>0.063<br>0.315<br>0.484|

_Sampling-Based Distribution + Few-shot Steering_

|No-CoT 0.003 0.414 0.698<br>Llama-8B CoT 0.006 0.440 0.697<br>R1 0.022 0.445 0.699|0.004 0.313 0.257<br>0.150 0.237 0.332<br>0.114 0.236 0.339|0.064 0.373 0.563<br>0.070 0.275 0.646<br>0.182 0.227 0.689|0.097 0.386 0.522<br>0.098 0.326 0.565<br>0.181 0.275 0.607|0.067 0.476 0.504<br>0.088 0.299 0.313<br>0.060 0.290 0.483|
|---|---|---|---|---|
|Qwen-14B<br>No-CoT<br>0.084<br>0.357<br>0.685<br>CoT<br>0.062<br>0.316<br>0.697<br>R1<br>0.121<br>0.290<br>0.692|0.151<br>0.208<br>0.348<br>0.266<br>0.175<br>0.394<br>0.322<br>0.158<br>0.389|0.087<br>0.298<br>0.634<br>0.121<br>0.282<br>0.646<br>0.137<br>0.257<br>0.673|0.087<br>0.320<br>0.570<br>0.139<br>0.324<br>0.579<br>0.209<br>0.281<br>0.601|0.084<br>0.417<br>0.504<br>0.037<br>0.333<br>0.222<br>0.068<br>0.310<br>0.488|
|Qwen-32B<br>No-CoT<br>0.101<br>0.381<br>0.687<br>CoT<br>0.130<br>0.281<br>0.709<br>R1<br>0.019<br>0.308<br>0.743|0.142<br>0.183<br>0.375<br>0.272<br>0.166<br>0.416<br>0.246<br>0.164<br>0.419|0.111<br>0.263<br>0.646<br>0.120<br>0.253<br>0.661<br>0.174<br>0.237<br>0.701|0.111<br>0.301<br>0.585<br>0.111<br>0.320<br>0.564<br>0.161<br>0.290<br>0.604|0.034<br>0.372<br>0.493<br>0.051<br>0.330<br>0.358<br>0.084<br>0.299<br>0.473|
|Llama-70B<br>No-CoT<br>0.025<br>0.433<br>0.703<br>CoT<br>0.077<br>0.322<br>0.715<br>R1<br>0.063<br>0.288<br>0.749|0.018<br>0.231<br>0.335<br>0.158<br>0.192<br>0.391<br>0.234<br>0.184<br>0.388|0.090<br>0.300<br>0.646<br>0.022<br>0.303<br>0.644<br>0.148<br>0.247<br>0.687|0.120<br>0.326<br>0.593<br>0.098<br>0.323<br>0.590<br>0.197<br>0.299<br>0.592|0.023<br>0.438<br>0.505<br>0.100<br>0.329<br>0.389<br>0.069<br>0.320<br>0.475|

Table 5: Performance on Random (randomly sampled) subsets of all datasets.

16

HS2 _↓_ GHC _↓_ Pos _↓_ Neg _↓_ Amb _↓_

_Verbalized Distribution &_ _**w/o**_ _Few-shot Steering_

_Verbalized Distribution + Few-shot Steering_

_Sampling-Based Distribution &_ _**w/o**_ _Few-shot Steering_

_Sampling-Based Distribution + Few-shot Steering_

Table 6: DistAlign Performance on HighVar (high annotation variance) subset of all datasets.

17
