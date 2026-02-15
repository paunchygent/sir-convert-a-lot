## Dependence-Aware Label Aggregation for LLM-as-a-Judge via Ising Models

Krishnakumar Balasubramanian [1] _[,]_ [2], Aleksandr Podkopaev [2],
Shiva Prasad Kasiviswanathan [2]

1Department of Statistics, University of California, Davis
2Amazon Web Services

February 2, 2026

**Abstract**

Large-scale AI evaluation increasingly relies on aggregating binary judgments from _K_ annotators, including LLMs used as judges. Most classical methods, e.g., Dawid-Skene or (weighted)
majority voting, assume annotators are conditionally independent given the true label _Y_ _∈_
_{_ 0 _,_ 1 _}_, an assumption often violated by LLM judges due to shared data, architectures, prompts,
and failure modes. Ignoring such dependencies can yield miscalibrated posteriors and even confidently incorrect predictions. We study label aggregation through a hierarchy of dependenceaware models based on Ising graphical models and latent factors. For class-dependent Ising
models, the Bayes log-odds is generally quadratic in votes; for class-independent couplings, it
reduces to a linear weighted vote with correlation-adjusted parameters. We present finite- _K_
examples showing that methods based on conditional independence can flip the Bayes label despite matching per-annotator marginals. We prove separation results demonstrating that these
methods remain strictly suboptimal as the number of judges grows, incurring nonvanishing excess risk under latent factors. Finally, we evaluate the proposed method on three real-world
datasets, demonstrating improved performance over the classical baselines.

### **1 Introduction**

Large-scale evaluation of modern AI systems increasingly relies on _aggregating_ _binary_ _judgments_
from multiple annotators that are predominantly LLMs used as judges. Given an item with unknown label _Y_ _∈{_ 0 _,_ 1 _}_ and _K_ noisy votes _J_ = ( _J_ 1 _, . . ., JK_ ) _∈{_ 0 _,_ 1 _}_ _[K]_, the core statistical problem
is to infer _Y_ from _J_ . Many classical aggregators such as majority vote, weighted majority vote, and
Dawid-Skene (DS) [12] estimators are built around the _conditional_ _independence_ (CI) assumption:
they treat annotators as independent voters given _Y_, i.e., P( _J|Y_ ) = [�] _j_ _[K]_ =1 [P(] _[J][j][|][Y]_ [ ).] [Under] [this]
assumption, the weighted majority vote estimator is Bayes-optimal, and the DS estimator provides a practical approach for estimating the weights using the popular Expectation-Maximization
algorithm, subject to appropriate identifiability conditions.
The CI assumption is however increasingly mismatched to contemporary evaluation pipelines,
especially for LLM judges, where correlations arise from shared pretraining corpora, architectures,
prompts, and failure modes [18, 24, 41]. Dependence is not a benign nuisance: it can fundamentally
change the information content of the votes. When judges are redundant or co-vary, aggregation
approaches based on the CI assumption (which we refer to as _CI-predictors_ and which are typically
based on weighted majority voting) can _over-count_ _agreement_ and yield systematically miscalibrated predictions. In Appendix B, we demonstrate this through a three-annotator example: when

1

_W_ [(1)] (when _Y_ = 1)
_W_ [(0)] (when _Y_ = 0)

Figure 1: **Graphical models for LLM-as-a-judge.** Conditional independence (CI); _(left)_ : judges
are independent given _Y_ (represented by lack arrows connecting the Judge LLMs). Class-dependent
Ising; _(right)_ : judges exhibit pairwise dependence whose pattern can change with the label ( _W_ [(0)] =
_W_ [(1)] ), enabling class information to affect directly the correlations among judges.

the dependence is captured via an Ising model explained shortly, the posterior prediction for the labels (assuming CI) predicts the opposite label with near-certainty, even given _correct_ per-annotator
marginals. This illustrates a key insight: misspecified dependence structure can dominate correct
marginal modeling.
In this work, we revisit label aggregation through the lens of _Ising_ _graphical_ _models_ [1], i.e.,
quadratic Markov random fields of the form

P( _J_ _| Y_ = _y_ ) _∝_ exp� _J_ _[⊤]_ _h_ [(] _[y]_ [)] + _J_ _[⊤]_ _W_ [(] _[y]_ [)] _J_ - _,_

for _J_ _∈{_ 0 _,_ 1 _}_ _[K]_ _,_ _y_ _∈{_ 0 _,_ 1 _}_ ; see Figure 1 for a graphical model illustration. Here _h_ [(] _[y]_ [)] _∈_ R _[K]_ is a
vector of _class-y_ _local_ _fields_ capturing per-judge bias/strength: _h_ [(] _j_ _[y]_ [)] controls how likely judge _j_ is
to output 1 under class _y_ (holding other votes fixed). The symmetric matrix _W_ [(] _[y]_ [)] _∈_ R _[K][×][K]_ (with
zero diagonal) is the _class-y_ _coupling_ matrix encoding pairwise dependencies: _Wjk_ [(] _[y]_ [)] _[>]_ [ 0 encourages]

judges _j_ and _k_ to co-vote 1, while _Wjk_ [(] _[y]_ [)] _\<_ 0 discourages co-voting and captures antagonistic or
compensatory behavior. In LLM-as-a-judge settings, _h_ [(] _[y]_ [)] reflects each judge’s label-conditional
tendency to vote for class 1, while _W_ [(] _[y]_ [)] represents persistent agreement/disagreement patterns
induced by shared, training data, architectures, and failure modes.
Building on this representation, we introduce the model hierarchy in Figure 2. The most
expressive model is the _class-dependent Ising model_, which allows class-specific interactions ( _W_ [(0)] =
_W_ [(1)] ) and yields Bayes log-odds that are generally _quadratic_ in the votes. An important special
case is the _class-independent_ _Ising_ _model_ where couplings are shared across classes ( _W_ [(0)] = _W_ [(1)] ):
in this case, the quadratic terms cancel in the likelihood ratio and the Bayes log-odds reduce to a
_linear_ weighted vote in _J_ . Importantly, dependence still matters—correlations are absorbed into
correlation-corrected weights and intercepts—allowing this model to discount redundant agreement
while retaining the simplicity of a linear aggregation rule.

**1.1** **Our** **Contributions**

- **Dependence-aware** **Model** **Hierarchy.** In Section 2, we formalize the model hierarchy
  spanning CI model, class-independent Ising model (shared interactions), and class-dependent
  Ising model (class-specific interactions). We derive the exact Bayes log-odds for class-dependent

1We note that the multiclass setting can be handled by working with Potts models [36].

2

**Conditional** **Independence** **(CI)**
Bayes-optimal: (weighted) linear aggregation

Figure 2: **Model** **hierarchy** **via** **set** **inclusion:** Conditional Independence (CI) _⊂_
Class-independent Ising _⊂_ Class-dependent Ising.

Ising model which is quadratic in votes, and show that under class-independent Ising model,
the Bayes rule reduces to a linear weighted vote with dependence-adjusted parameters.

- **Separation** **Results.** In Section 3, we establish a sharp separation result under the classdependent Ising model. We show that there exist regimes where each judge is better than
  random, yet the CI-predictor still makes a constant fraction of errors by misinterpreting correlated “wrong-mode” agreement as strong evidence. In contrast, the Bayes-optimal predictor
  exploits the dependence structure and achieves vanishing error as the number of judges grows,
  creating non-vanishing risk separation between the two methods.

- **Relation** **to** **Factor** **Models.** In the crowdsourcing literature, another way to model judge
  dependence is via _latent-factor_ _model_ with a shared random effect _Z_ (independent of _Y_ )
  such that judges are conditionally independent only given ( _Y, Z_ ): P( _J_ _|_ _Y, Z_ ) = [�] _j_ _[K]_ =1 [P(] _[J][j]_ _[|]_
  _Y, Z_ ) [42, 43]. We show that the CI-predictor which ignores _Z_ can remain strictly suboptimal
  when data are generated from such factor model, _even_ _as_ _K_ _→∞_ . For weak coupling, we
  show that latent-factor models induce an approximately low-rank Ising structure, placing
  them between CI and class-dependent Ising model. The details are deferred to Appendix C.3.

- **Experimental** **Validation.** We evaluate the proposed aggregation method on three realworld tasks: relevance, toxicity, and summarization evaluations, using six judge models:
  Claude Sonnet 4.5, Claude Haiku 4.5, OpenAI gpt-oss-120b, Llama 4 Maverick 17B Instruct,
  Llama 4 Scout 17B Instruct, and DeepSeek-R1. In Appendix F, we include synthetic simulations that illustrate our theoretical separation results.

We defer a discussion placing our work in the context the larger literature on LLM-as-a-judge,
unsupervised label aggregation and crowdsourcing to Appendix A.

### **2 Dependent LLMs-as-a-Judge Models**

Suppose that we observe _n_ independent items. Item _i_ has an unobserved label _Yi_ _∈{_ 0 _,_ 1 _}_, with
prior P( _Yi_ = 1) = _π_ _∈_ (0 _,_ 1), and is annotated by _K_ judges producing a binary vote vector _Ji_ =

3

( _Ji_ 1 _, . . ., JiK_ ) _∈{_ 0 _,_ 1 _}_ _[K]_ . We assume items are independent and model _within-item_ _dependencies_
among judges via Ising (pairwise MRF) distribution conditional on the label: P( _{Ji, Yi}_ _[n]_ _i_ =1 [)] =

- _ni_ =1 [P(] _[Y][i]_ [) P(] _[J][i]_ _[|][ Y][i]_ [).] [This] [makes] [the] [label] [inference] [problem] [for] [each] [item] [separable] [given] [model]
  parameters [2] .
  In LLM-as-a-judge pipelines, the within-item dependencies arise due to shared pretraining data,
  architectures, and prompt templates (leading to label-independent redundancy and shared failure
  modes), while in other settings dependence itself can be label-dependent (e.g., certain classes trigger
  common hallucination patterns or refusal behaviors), motivating two practically distinct regimes: a
  _class-dependent_ structure _W_ [(0)] = _W_ [(1)] that allows correlation patterns to change with the true label
  and a _class-independent_ interaction structure _W_ [(0)] = _W_ [(1)] that captures persistent correlations
  across all items.

**2.1** **Class-dependent** **Ising** **Model**

In the most general form, the class-conditional distribution of the _K_ votes is allowed to differ across
labels: for each _y_ _∈{_ 0 _,_ 1 _}_, we have

- _K_

1
P( _Ji_ _| Yi_ = _y_ ) =

[exp]
_Z_ [(] _[y]_ [)]

_h_ [(] _j_ _[y]_ [)] _[J][ij]_ [+] [1]

2

_j_ =1

2

- _Wjk_ [(] _[y]_ [)] _[J][ij][J][ik]_ _,_ (1)

_j_ = _k_

where _h_ [(] _[y]_ [)] _∈_ R _[K]_ are class- _y_ local fields (biases), _W_ [(] _[y]_ [)] _∈_ R _[K][×][K]_ is a symmetric coupling matrix
with zero diagonal, and _Z_ [(] _[y]_ [)] is the corresponding partition function. This model captures the
possibility that judges are correlated _even after conditioning on the label_ where the strength/pattern
of correlation may itself depend on the class.
**Bayes-optimal** **Posterior.** For a single item, we write _J_ = ( _J_ 1 _, . . ., JK_ ). The Bayes’ rule gives
posterior log-odds:

[= 1] _[ |][ J]_ [)]
Λ( _J_ ) := log [P(] _[Y]_

P( _Y_ = 0 _| J_ )

_π_ _[|][ Y]_ [= 1)]
= log _[P]_ [(] _[J]_
1 _−_ _π_ [+ log] _P_ ( _J_ _| Y_ = 0)

_π_
= log
1 _−_ _π_ [+]

_K_

∆ _hj Jj_ + [1]

2

_j_ =1

2

∆ _Wjk JjJk_ + ∆ _Z,_

_j_ = _k_

where ∆ _hj_ := _h_ [(1)] _j_ _−_ _h_ [(0)] _j_ [,] [∆] _[W][jk]_ [:=] _[W]_ [ (1)] _jk_ _[−]_ _[W]_ [ (0)] _jk_ and ∆ _Z_ := _−_ log _Z_ [(1)] + log _Z_ [(0)] . The term
∆ _Z_ is constant in _J_ (for fixed parameters and fixed _K_ ) and can be absorbed into the intercept.
Since _W_ [(] _[y]_ [)] is symmetric with zero diagonal, one can equivalently rewrite the quadratic term as
21 - _j_ = _k_ [∆] _[W][jk][J][j][J][k]_ [=][ �] 1 _≤j\<k≤K_ [∆] _[W][jk][ J][j][J][k][.]_ [Therefore,] [the] [Bayes-optimal] [predictor] [takes] [form:]

_g_ _[⋆]_ ( _J_ ) = **1** _{_ Λ( _J_ ) _≥_ 0 _}_

- - (2)

_bjkJjJk_ _≥_ 0 _,_

1 _≤j\<k≤K_

= **1** _b_ 0 +

_K_

-

_ajJj_ +

_j_ =1 1 _≤j\<k_

where _aj_ = ∆ _hj_, _bjk_ = ∆ _Wjk_ and _b_ 0 = log 1 _−ππ_ [+ ∆] _[Z]_ [.] [When] _[W]_ [ (1)] [=] _[W]_ [ (0)][,] [the] [optimal] [decision]
boundary is _quadratic_ in the votes since class information may be present not only in marginal
accuracies (fields) but also in _label-dependent_ _correlation_ _structure_ (couplings).

2The literature on Ising models use spins: _±_ 1. Our inference algorithm is unchanged under the bijection _Xij_ =
2 _Jij_ _−_ 1; we keep _Y, J_ _∈{_ 0 _,_ 1 _}_ throughout for consistency.

4

**2.2** **Class-Independent** **Couplings**

A common and interpretable special case is one in which the _dependence_ _structure_ among judges
is shared across both classes but individual biases and accuracies shift with the label. Specifically,
we assume

1 - - _[K]_
P( _Ji_ _| Yi_ = _y_ ) =

[exp]
_Z_ [(] _[y]_ [)]

_j_ =1

2 [1] [)] _[c][j]_ - _Jij_ + [1]

- _hj_ + ( _y −_ [1]

2

-

_Wjk JijJik_ _,_ (3)

_j_ = _k_

where _hj_ represents a label-independent baseline field, _cj_ controls how the label shifts judge _j_ ’s
field, and _W_ is a shared symmetric coupling matrix (with zero diagonal). Here, the normalizer _Z_ [(] _[y]_ [)]

may still depend on _y_ since the fields differ across classes.
**Bayes-optimal** **Posterior.** Under (3), the posterior log-odds simplify substantially:

log [P(] _[Y]_ [= 1] _[ |][ J]_ [)]

P( _J_ _| Y_ = 0)

[P(] _[Y]_ [= 1] _[ |][ J]_ [)] _π_ [P(] _[J]_ _[|][ Y]_ [= 1)]

P( _Y_ = 0 _| J_ ) [= log] 1 _−_ _π_ [+ log] P( _J_ _| Y_ = 0)

_π_
= log
1 _−_ _π_ [+]

_K_ (4)

_cjJj_ + ∆ _Z,_

_j_ =1

where ∆ _Z_ = _−_ log _Z_ [(1)] + log _Z_ [(0)] is a constant in _J_ . The quadratic terms cancel since the coupling
matrix is shared across the two classes. Therefore, the Bayes-optimal predictor is a _linear_ threshold
rule:

- - _[K]_
    _g_ _[⋆]_ ( _J_ ) = **1**
-

_cjJj_ + _b_ 0 _≥_ 0 _,_

_j_ =1

(5)

_π_
_b_ 0 = log
1 _−_ _π_ [+ ∆] _[Z][.]_

If one prefers _±_ 1 labels instead of _{_ 0 _,_ 1 _}_, one can define centered spins _Xj_ := 2 _Jj_ _−_ 1 _∈{±_ 1 _}_ .
Then [�] _j_ _[c][j][J][j]_ [=] [1] 2 - _j_ _[c][j][X][j]_ [+] [1] 2 - _j_ _[c][j]_ [,] [so] [the] [rule] [remains] [a] [weighted] [vote] [on] _[X]_ [after] [absorbing]

[1] 2 - _j_ _[c][j][X][j]_ [+] [1] 2

Then [�] _j_ _[c][j][J][j]_ [=] [1] 2 - _j_ _[c][j][X][j]_ [+] [1] 2 - _j_ _[c][j]_ [,] [so] [the] [rule] [remains] [a] [weighted] [vote] [on] _[X]_ [after] [absorbing]

12 - _j_ _[c][j]_ [into] [the] [intercept.] If _W_ _≡_ 0, then the judges are conditionally independent given _Y_
and (3) reduces to a product of Bernoulli marginals: P( _J_ _|_ _Y_ = _y_ ) = [�] _j_ _[K]_ =1 [P(] _[J][j]_ _[|]_ _[Y]_ [=] _[y]_ [)] [with]
P( _Jj_ = 1 _|_ _Y_ = _y_ ) = _σ_ - _hj_ + ( _y_ _−_ [1] [)] _[c][j]_ �, where _σ_ ( _t_ ) = (1 + _e_ _[−][t]_ ) _[−]_ [1] . In this case, the per-judge

P( _Jj_ = 1 _|_ _Y_ = _y_ ) = _σ_ - _hj_ + ( _y_ _−_ [1] 2 [)] _[c][j]_ �, where _σ_ ( _t_ ) = (1 + _e_ _[−][t]_ ) _[−]_ [1] . In this case, the per-judge

contribution to the posterior log-odds can be written as an affine function of _Jj_ :

log [P(] _[J][j]_ _[|][ Y]_ [= 1)] - logit( _p_ [(1)] _j_ [)] _[ −]_ [logit(] _[p]_ _j_ [(0)][)] - + log 1 _−_ _p_ [(1)] _j_ _,_

P( _Jj_ _| Y_ = 0) [=] _[ J][j]_ 1 _−_ _p_ [(0)] _j_

where _p_ [(] _j_ _[y]_ [)] := P( _Jj_ = 1 _|_ _Y_ = _y_ ). Summing over _j_ recovers the classical CI or Naive-Bayes
linear aggregation rule with weights equal to differences of logits; in the parameterization (3),
logit( _p_ [(1)] _j_ [)] _[−]_ [logit(] _[p]_ _j_ [(0)][) =] _[ c][j][.]_ [ When] _[ W]_ [= 0 but is] _[ shared across classes]_ [, correlations do not introduce]
quadratic terms into the Bayes log-odds (they cancel in (4)), and the Bayes decision remains linear
in _J_ . Nevertheless, correlations still matter statistically: they change the joint law of _J_ within each
class and therefore affect likelihoods, partition functions (hence the intercept _b_ 0), and parameter
estimation from finite data. In contrast, if the couplings differ across classes ( _W_ [(1)] = _W_ [(0)] ), then
class information is present in the dependence structure and the Bayes decision becomes quadratic
as in (2).
For the sake of completeness, we discuss the CI model with asymmetric errors (which leads to
weighted majority vote aggregators) in Appendix C.1. We also briefly discuss the similarities and
differences with the linear and quadratic discriminant analysis model, that are standard Gaussian
models (as opposed to the binary Ising models) in Appendix C.2.

5

### **3 Separation Results**

In this section, we use our model hierarchy to clarify when standard aggregation rules are justified for LLM-as-a-judge pipelines and when those fail. Weighted majority vote (with sufficiently
accurate weights) is Bayes-optimal under conditional independence (CI) Ai et al. [2, Theorem 1].
However, as argued in the introduction and illustrated by our motivating examples (Appendix B),
satisfying CI is often implausible for LLM judges due to shared pretraining corpora, similar architectures, reused prompt templates, and common safety/refusal or hallucination failure modes.
These dependencies are not merely noise: they can encode item properties (e.g., difficulty or trigger
patterns) and the redundancy of evidence across judges.
We show a separation (in terms of risk) between majority voting procedures and the Bayesoptimal predictor under two dependence mechanisms relevant to LLM-as-a-judge: (a) shared latent
factors inducing low-rank correlations (Appendix C.3.1) and (b) interaction-driven dependence
captured by the Curie-Weiss model, a special case of the Ising model, with strong agreement modes
(Section 3.1). These separation results clearly demonstrate the limitations in expressive power of
schemes such as majority voting. The proofs are deferred to Appendix E.

**3.1** **Sub-optimality** **of** **CI-predictor** **under** **Ising** **Dependence**

The risk of a binary aggregator _g_ in our setting is defined as _R_ ( _g_ ) := P( _g_ ( _J_ ) = _Y_ ). We start by
establishing a separation result in terms of risk between a special case of Ising model, namely the
Curie-Weiss model, which has been widely used in opinion dynamics [5]. Informally, we show that
even with infinitely many judges, any CI-predictor remains strictly suboptimal, whereas there exists
a Bayes predictor that leverages dependence (quadratic structure) to classify essentially perfectly.

**Theorem** **1** (Nonvanishing Bayes vs. CI Separation for Class-conditional Ising Models) **.** _Fix_ _a_
_prior_ P( _Y_ = 1) = _π_ _∈_ (0 _,_ 1) _._ _For_ _each_ _K_ _≥_ 1 _,_ _let_ _J_ = ( _J_ 1 _, . . ., JK_ ) _∈{_ 0 _,_ 1 _}_ _[K]_ _denote_ _the_ _K_
_judges’_ _votes_ _for_ _a_ _single_ _item_ _and_ _define_ _the_ _recoded_ _spins_ _Xj_ := 2 _Jj_ _−_ 1 _∈{−_ 1 _,_ +1 _}_ _and_ _let_

_MK_ := _K_ 1 - _Kj_ =1 _[X][j]_ _[∈]_ - _−_ 1 _, −_ 1 + _K_ [2] _[, . . .,]_ [ 1] - _._ _Assume_ _the_ _following_ class-conditional Curie-Weiss

Ising _model:_ _there_ _exist_ _constants_ 0 _< β_ 0 _\<_ 1 _< β_ 1 _such_ _that,_ _conditional_ _on_ _Y_ = _y_ _∈{_ 0 _,_ 1 _},_

1 - _βy_
P( _X_ = _x | Y_ = _y_ ) =
_ZK_ ( _βy_ ) [exp] 2 _K_

- - _[K]_ _xj_ �2� _,_ (6)

_j_ =1

_for_ _x_ _∈{−_ 1 _,_ +1 _}_ _[K]_ _._ _Equivalently_ _(writing_ _xj_ = 2 _jj_ _−_ 1 _),_ _this_ _is_ _a_ _special_ _case_ _of_ _the_ _{_ 0 _,_ 1 _}-Ising_

```
      _form_ (1) _with_ _h_ [(] _j_ _[y]_ [)] = _−_ 2 _βy_ 1 _−_ [1]
```

_K_ [1] - _and_ _Wjk_ [(] _[y]_ [)] [=] [4] _K_ _[β][y]_

_[y]_ ( _j_ = _k_ ) _,_ _up_ _to_ _an_ _additive_ _constant_ _absorbed_

_K_

_into_ _Z_ [(] _[y]_ [)] _._
_Let_ _gK_ _[⋆]_ _[be]_ _[the]_ _[Bayes-optimal]_ _[predictor]_ _[under]_ _[the]_ _[true]_ _[model]_ [(6)] _[.]_ _[Let]_ _[g]_ _K_ [ind] _be_ _the_ _population_
_CI-predictor_ _that_ _replaces_ _the_ _true_ _joint_ _by_ _the_ _product_ _of_ _true_ _one-dimensional_ _marginals,_ _i.e.,_
P [ind] ( _J_ = _j_ _| Y_ = _y_ ) := [�] _r_ _[K]_ =1 _[q]_ _y_ _[j][r]_ [(1] _[ −]_ _[q]_ _y_ [)][1] _[−][j][r]_ _[with]_ _[q]_ _y_ [:= P(] _[J]_ _r_ [= 1] _[ |][ Y]_ [=] _[ y]_ [)] [(] _[independent]_ _[of]_ _[r]_ [)] _[,]_ _[and]_
_then_ _thresholds_ _the_ _induced_ _posterior_ P [ind] ( _Y_ = 1 _| J_ ) _at_ 1 _/_ 2 _._ _Then_ _the_ _following_ _results_ _hold:_

_1._ _**(CI**_ _**Collapses**_ _**to**_ _**the**_ _**Prior)**_ _For_ _every_ _K_ _and_ _y_ _∈{_ 0 _,_ 1 _},_ _one_ _has_ _qy_ = [1]

_**(CI**_ _**Collapses**_ _**to**_ _**the**_ _**Prior)**_ _For_ _every_ _K_ _and_ _y_ _∈{_ 0 _,_ 1 _},_ _one_ _has_ _qy_ = 2 _[.]_ _[Consequently,]_

P [ind] ( _Y_ = 1 _| J_ ) = _π_ _for_ _all_ _J,_ _so_ _gK_ [ind][(] _[J]_ [)] _[ ≡]_ **[1]** _[{][π]_ _[≥]_ [1] 2 _[}][,]_ _[and]_ _[R]_ [(] _[g]_ _K_ [ind][) = min] _[{][π,]_ [ 1] _[ −]_ _[π][}][,][ ∀][K][.]_

[1] 2 _[}][,]_ _[and]_ _[R]_ [(] _[g]_ _K_ [ind][) = min] _[{][π,]_ [ 1] _[ −]_ _[π][}][,][ ∀][K][.]_

_2._ _**(Bayes**_ _**Risk**_ _**Vanishes)**_ _Let_ _m⋆_ = _m⋆_ ( _β_ 1) _∈_ (0 _,_ 1) _denote_ _the_ _unique_ _positive_ _solution_ _to_

6

_m_ = tanh( _β_ 1 _m_ ) _._ _Then_ _for_ _any_ _fixed_ _threshold_ _t ∈_ (0 _, m_ [2] _⋆_ [)] _[,]_ _[the]_ _[quadratic]_ _[statistic]_ _[test:]_

_g_ ˜ _K_ ( _J_ ) := **1** _{MK_ ( _J_ ) [2] _≥_ _t},_

_MK_ ( _J_ ) = [1]

_K_

_K_

(2 _Jj_ _−_ 1) _,_

_j_ =1

_satisfies_ _R_ (˜ _gK_ ) _→_ 0 _as_ _K_ _→∞._ _Hence_ _R_ ( _gK_ _[⋆]_ [)] _[ →]_ [0] _[as]_ _[K]_ _[→∞][.]_

_3._ _**(Nonvanishing**_ _**Separation)**_ _We_ _have:_

```
        -
```

lim _R_ ( _gK_ [ind][)] _[ −]_ _[R]_ [(] _[g]_ _K_ _[⋆]_ [)] = min _{π,_ 1 _−_ _π}_ _>_ 0 _._
_K→∞_

Theorem 1 gives a clean population-level separation between the Bayes-optimal predictor and
a CI-predictor when the judges are _dependent_ given the label. We consider a setting where, for
each label _y_ _∈{_ 0 _,_ 1 _}_, the _K_ votes are drawn from a class-conditional Ising model. In the particular
Curie-Weiss specialization used in the theorem, the conditional law depends only on the _global_
_magnetization_ _MK_ and the dependence strength differs across classes: the negative class is in a
_high-temperature_ regime ( _β_ 0 _\<_ 1), while the positive class is in a _low-temperature_ regime ( _β_ 1 _>_ 1).
In this model the two classes have the _same_ one-dimensional marginals: for every judge _j_ and
both labels _y_ _∈{_ 0 _,_ 1 _}_, P( _Jj_ = 1 _|_ _Y_ = _y_ ) = 1 _/_ 2 _._ Thus, looking at each judge in isolation provides
no information about the label. The only distinguishing signal is in the _dependence_ _structure_ :
under _Y_ = 1 the votes exhibit strong global alignment (many judges tend to agree), whereas
under _Y_ = 0 they do not. The CI-predictor replaces the true joint likelihood by a product of
these one-dimensional marginals. Since the marginals are identical across classes, under CI, the
likelihood ratio is identically 1, so the posterior stays equal to the prior _π_ for every vote vector _J_ .
Consequently, the CI-predictor ignores the data entirely and achieves risk _R_ ( _gK_ [ind][) = min] _[{][π,]_ [ 1] _[−]_ _[π][}][,]_
independently of _K_ .
In contrast, the Bayes-optimal posterior uses the correct class-conditional joint likelihood, which
depends on quadratic (pairwise) interactions among votes and, in this Curie-Weiss case, can be
expressed through the statistic _MK_ [2] [.] [As] _[K]_ [grows,] [the] [magnetization] [concentrates] [at] [0] [under] [the]
high-temperature class ( _Y_ = 0) and concentrates near a nonzero value under the low-temperature
class ( _Y_ = 1) (up to a random global sign flip). Therefore, a simple quadratic rule such as
**1** _{MK_ [2] _[≥]_ _[t][}]_ [(for] [any] [fixed] _[t]_ [between] [0] [and] [the] [squared] [limiting] [magnetization] [under] _[Y]_ [=] [1)]
separates the two classes with vanishing error as _K_ _→∞_ . Since the Bayes rule is optimal, its risk
also converges to 0. Putting the two pieces together, the Bayes-optimal risk goes to zero while the
CI risk stays bounded away from zero.

**3.2** **Extension** **to** **Informative** **Marginals**

The Curie-Weiss separation example in Theorem 1 uses the zero-field Curie-Weiss model, which is
invariant under the global flip _X_ _�→−X_ . This symmetry forces _q_ 0 = _q_ 1 = P( _Jj_ = 1 _|_ _Y_ = _y_ ) = 2 [1]

for both classes, so a CI-predictor that only uses one-dimensional marginals collapses to the prior.
While this may look like a “corner case,” the underlying failure mechanism is _not_ : the CI-predictor
cannot exploit class information carried by _dependence_ _structure_ (correlation/interaction patterns),
and this can remain true even when individual marginals are (slightly) informative.
At a basic level, risks vary continuously with the data-generating law: if _P_ and _Q_ are two joint
distributions on ( _Y, J_ ) and _d_ TV( _P, Q_ ) := sup _A |P_ ( _A_ ) _−_ _Q_ ( _A_ ) _|_ is their total variation distance, then
for any classifier _g_, _|RP_ ( _g_ ) _−RQ_ ( _g_ ) _| ≤_ _d_ TV( _P, Q_ ), and in particular we have _|RP_ _[⋆]_ _[−][R]_ _Q_ _[⋆]_ _[| ≤]_ _[d]_ [TV][(] _[P, Q]_ [),]

7

because _RP_ ( _g_ ) = _P_ ( _g_ ( _J_ ) _̸_ = _Y_ ) is the probability of a measurable event, where _RP_ _[⋆]_ [is Bayes-optimal]
risk under distribution _P_ . Thus, for any fixed (moderate) _K_, the large finite-sample gaps exhibited
by the symmetric Curie-Weiss example persist under small perturbations of the class-conditional
distributions, including perturbations that move the marginals away from 1 _/_ 2.
The next result gives an explicit _asymptotic_ variant in which each judge is individually better
than random ( _q_ 0 _\<_ 1 _/_ 2 _\<_ _q_ 1), yet the CI risk remains bounded away from zero while the Bayesoptimal risk still vanishes as _K_ _→∞_ . The key idea is to retain _phase_ _coexistence_ in the lowtemperature class so that, with constant probability, the judges collectively enter a “wrong-sign”
agreement mode that a CI-predictor interprets as decisive evidence for the wrong label, whereas
the Bayes-optimal predictor uses a dependence-sensitive statistic (here _|MK|_ ) to identify the true
class.

**Theorem** **2** (Curie-Weiss separation with informative marginals) **.** _Let_ _Y_ _∈{_ 0 _,_ 1 _}_ _with_ P( _Y_ =

1. = _π_ _∈_ (0 _,_ 1) _._ _For_ _each_ _K_ _≥_ 1 _,_ _define_ _spins_ _X_ = ( _X_ 1 _, . . ., XK_ ) _∈{−_ 1 _,_ +1 _}_ _[K]_ _and_ _votes_
   _Jj_ = ( _Xj_ + 1) _/_ 2 _∈{_ 0 _,_ 1 _}._ _Let_ _the_ _class-conditional_ _laws_ _of_ _X_ _be_ _Curie-Weiss_ _models_ _with_ _(possibly_
   _K-dependent)_ _external_ _fields:_

_K_

-

_xj_ _,_ (7)

_j_ =1

1 - _βy_
P( _X_ = _x | Y_ = _y_ ) = exp

2 _K_
_ZK_ [(] _[y]_ [)]

- - _[K]_ �2

_xj_ + _hy,K_

_j_ =1

_for_ _y_ _∈{_ 0 _,_ 1 _}._ _Assume_ _parameters_ _satisfy:_

_1._ _(High-temperature_ _Class)_ _β_ 0 _∈_ (0 _,_ 1) _and_ _h_ 0 _,K_ _≡_ _h_ 0 _\<_ 0 _is_ _a_ _fixed_ _negative_ _constant;_

_2._ _(Low-temperature_ _Class_ _with_ _Weak_ _Symmetry_ _Breaking)_ _β_ 1 _>_ 1 _and_ _h_ 1 _,K_ = _c/K_ _with_ _some_
_fixed_ _c >_ 0 _._

_Let_ _MK_ := _K_ [1] - _Kj_ =1 _[X][j]_ _[∈]_ \[[] _[−]_ [1] _[,]_ [ 1]\] _[be]_ _[the]_ _[magnetization.]_ _[Let]_ _[m]_ [0] _[∈]_ [(] _[−]_ [1] _[,]_ [ 0)] _[be]_ _[the]_ _[unique]_ _[solution]_ _[of]_

_the_ _mean-field_ _equation_ _m_ 0 = tanh( _β_ 0 _m_ 0 + _h_ 0) _,_ _and_ _let_ _m⋆_ = _m⋆_ ( _β_ 1) _∈_ (0 _,_ 1) _be_ _the_ _unique_ _positive_
_solution_ _of_ _m⋆_ = tanh( _β_ 1 _m⋆_ ) _._ _Define_

_e_ _[cm][⋆]_ - 1 _p_ := _,_

_e_ _[cm][⋆]_ + _e_ _[−][cm][⋆]_ [=] _[ σ]_ [(2] _[cm][⋆]_ [)] _[ ∈]_ 2 _[,]_ [ 1]

_q_ 0 := P( _J_ 1 = 1 _| Y_ = 0) = [1 +] _[ m]_ [0]

_[ m]_ [0]
_∈_ 0 _,_ [1]
2 2

2

_,_

```
             - 1
```

_q_ 1 := P( _J_ 1 = 1 _| Y_ = 1) = [1 + (2] _[p][ −]_ [1)] _[m][⋆]_ _∈_ _._

2 2 _[,]_ [ 1]

_Assume_ _additionally_ _that_

1 _−_ _m⋆_

_< q_ 0 _⇐⇒_ _m⋆_ _>_ 1 _−_ 2 _q_ 0 _._ (8)
2

_Let_ _gK_ _[⋆]_ _[denote]_ _[the]_ _[Bayes]_ _[predictor]_ _[under]_ _[the]_ _[true]_ _[model]_ [(7)] _[.]_ _[Let]_ _[g]_ _K_ [ind] _denote_ _the_ _population_ _CI-_
_predictor that replaces_ P( _J_ _| Y_ = _y_ ) _by the product of the true marginals_ [�] _j_ _[K]_ =1 _[q]_ _y_ _[J][j]_ [(1] _[−][q]_ _y_ [)][1] _[−][J][j]_ _[.Then,]_
_the_ _following_ _hold:_

_1._ _**(Informative**_ _**Marginals)**_ _Each_ _judge_ _is_ _individually_ _better_ _than_ _random:_ _q_ 0 _\<_ 21 _[\<]_ _[q]_ [1]
_(equivalently,_ _specificity_ 1 _−_ _q_ 0 _>_ [1] _[and]_ _[sensitivity]_ _[q]_ [1] _[>]_ [1] _[).]_

[1] 2 _[and]_ _[sensitivity]_ _[q]_ [1] _[>]_ [1] 2

2 _[).]_

_2._ _**(Bayes**_ _**Risk**_ _**Vanishes)**_ _For_ _any_ _fixed_ _threshold_ _t_ _satisfying_ _|m_ 0 _| < t < m⋆,_ _the_ _aggregator_
_g_ ˜ _K_ ( _J_ ) := **1** _{|MK| ≥_ _t}_ _has_ _R_ (˜ _gK_ ) _→_ 0 _as_ _K_ _→∞._ _Consequently,_ _R_ ( _gK_ _[⋆]_ [)] _[ →]_ [0] _[.]_

8

Dataset Class-Dep. Ising (ours) Class-Indep. Ising (ours) CI-WMV CI-UMV

Table 1: Test accuracy for the various methods on the three datasets. Numbers are averages over
20 trials. CI-WMV and CI-UMV correspond to weighted and uniform majority vote both of which
operator under conditional independence assumptions. Class-Dep. and Class-Indep. refer to classdependent and class-independent Ising models, respectively.

_3._ _**(CI**_ _**Remains**_ _**Bounded**_ _**away**_ _**from**_ _**Bayes)**_ _As_ _K_ _→∞,_ _we_ _have_ _R_ ( _gK_ [ind][)] _[→]_ _[π]_ [(1] _[ −]_ _[p]_ [)] _[,]_
_and_ _hence_ lim _K→∞_ - _R_ ( _gK_ [ind][)] _[ −]_ _[R]_ [(] _[g]_ _K_ _[⋆]_ [)] - _≥_ _π_ (1 _−_ _p_ ) _>_ 0 _._

**Remark** **1** (Continuity viewpoint) **.** _In_ _Theorem_ _2,_ _the_ _limiting_ _CI_ _error_ _is_ _π_ (1 _−_ _p_ ) _with_ _p_ =
_σ_ (2 _cm⋆_ ) _,_ _which_ _varies_ _continuously_ _with_ _the_ _“weak_ _symmetry-breaking”_ _strength_ _c._ _As_ _c_ _↓_ 0 _,_ _one_
_has_ _p →_ 1 _/_ 2 _and_ _q_ 1 _↓_ 1 _/_ 2 _,_ _recovering_ _the_ _symmetric_ _example;_ _for_ _any_ _c >_ 0 _,_ _the_ _marginals_ _become_
_informative_ _(q_ 1 _>_ 2 [1] _[)]_ _[yet]_ _[CI]_ _[still]_ _[makes]_ _[errors]_ _[on]_ _[a]_ _[constant]_ _[fraction]_ [(1] _[ −]_ _[p]_ [)] _[of]_ _[the]_ _[positive-class]_

_items_ _because_ _it_ _thresholds_ _the_ sign _of_ _the_ _vote_ _proportion,_ _whereas_ _Bayes_ _exploits_ _the_ _dependence-_
_induced_ _structure_ _(here,_ _large_ _|MK|_ _regardless_ _of_ _sign)._ _Thus_ _the_ _separation_ _is_ _robust:_ _it_ _is_ _driven_
_by_ _a_ _persistent_ _correlated_ _“wrong-sign”_ _mode,_ _not_ _by_ _the_ _exact_ _equality_ _qy_ = 1 _/_ 2 _._

The separation results in this section are interesting for two reasons. First, they show that the
limitations with the CI assumption are _structural_, not a finite-judge artifact: even as _K_ _→∞_, the
CI-predictor remain strictly suboptimal because it cannot exploit dependence-induced information
or distinguish redundant agreement from independent evidence (Ising interactions). Second, they
explain why LLM ensembles can become overconfident for the wrong reasons: if judges share a
failure mode, their agreement should be discounted rather than counted multiple times, which
CI weighting cannot do. Practically, this suggests evaluation pipelines should not rely solely on
per-judge accuracies or majority counts, but should monitor and model dependence among judges
(e.g., residual correlations after accounting for label uncertainty). When dependence is present, our
results motivate moving up the hierarchy: from CI to various Ising models, to improve accuracy,
calibration, and uncertainty for downstream decisions.

### **4 Experimental Evaluation**

For all experimental results, we use the Expectation-Maximization algorithm for posterior label
prediction. We defer the details to Appendix D. Simulation results comparing weighted (with the
weights estimated by EM algorithm) and uniform majority voting are provided in Appendix F.1.
Simulation results regarding CI-predictor and factor/Ising model predictors are provided in Appendix F. Below, we provide experiments on real-world datasets.

**4.1** **Real** **World** **Datasets**

We consider LLMaaJ label aggregation in three tasks: relevance, toxicity, and summarization
assessment. We use the following models as judges: (a) Claude Sonnet 4.5, (b) Claude Haiku 4.5,
(c) OpenAI gpt-oss-120b [33], (d) Llama 4 Maverick 17B Instruct, (e) Llama 4 Scout 17B Instruct,
and (f) DeepSeek-R1 [13]. For all models, the temperature parameter is set to zero. The prompts
used in our evaluations are deferred to Appendix G.3.

9

**Relevance.** We use the WikiQA dataset [44] to evaluate query-passage relevance classification, a
task which arises in the context of retrieval-augmented generation (RAG). The dataset consists of
natural language questions paired with multiple sentences extracted from Wikipedia. Each sentence
is annotated with a binary label which indicates whether it correctly answers the question at hand.
To construct inputs suitable for the relevance classification, we collect all the sentences associated
with each question and concatenate them into a single text passage. The resulting passage is labeled
relevant to the question if and only if at least one of the original sentences is labeled as a correct
answer; see examples in Appendix G.1. In our evaluation, we use all available splits for the original
dataset, resulting in approximately 3000 evaluation instances.
**Toxicity.** We use the Jigsaw Unintended Bias in Toxicity Classification dataset [1] for toxicity
classification. We use comments from the private leaderboard test set, filtering for those with
at least five human annotators and a minimum length of 100 characters. To ensure balanced
representation across all toxicity levels, we use stratified sampling based on comment toxicity
scores, i.e., the fraction of annotators who marked a comment as toxic. We randomly sample 1000
comments from each of the four toxicity score buckets: \[0 _,_ 0 _._ 25), \[0 _._ 25 _,_ 0 _._ 5), \[0 _._ 5 _,_ 0 _._ 75), \[0 _._ 75 _,_ 1\],
and label a comment as toxic (positive class) if at least half of the annotators marked it as toxic.
Additional preprocessing steps are deferred to Appendix G.2.
**Summarization.** We use the CNN/DailyMail news dataset [20, 37] for summarization assessment. The original dataset contains news articles along with short author-written summaries. For
[binary summarization assessment, we use a preprocessed variant of the dataset from Arize Phoenix](https://arize.com/docs/phoenix/evaluation/running-pre-tested-evals/summarization-eval)
[summarization](https://arize.com/docs/phoenix/evaluation/running-pre-tested-evals/summarization-eval) benchmark. This benchmark augments a subset of the original articles and summaries with synthetically generated incorrect summaries designed to resemble correct ones while
containing factual inconsistencies. The dataset contains 1100 instances with approximately the
same number of correct and incorrect summaries.
We conducted two experiments on those datasets: (i) studying the effect of varying the number
of training samples _n_ while keeping the number of judges fixed ( _K_ = 6), and (ii) studying effect of
varying _K_ while keeping the number of training samples _n_ fixed at roughly 10%–20% of the overall
dataset. We compared the class-independent Ising-predictors, class-dependent Ising-predictors, and
CI-predictors (specifically, the weighted majority vote procedure resulting from the asymmetric
models described in Appendix C.1). For these experiments, we randomly sampled the training
data and the judges and report the average test accuracy (and standard error) over 20 trials in
Figure 3.
From Figure 3, we note that the two Ising predictors invariably outperform the CI-predictor once
the number of training samples and the number of judges exceed a modest threshold (and in some
regimes even with fewer training samples). As a summary, in Table 1, we also report the result of
comparing the aforementioned procedures, along with the uniform majority voting procedure, when
all six judges are used and when the maximum amount of training data is used for each dataset (i.e.,
2500 samples for relevance, 3000 samples for toxicity, and 1000 samples for summarization tasks).
We notice that Ising models outperform (weighted) majority voting procedures. In particular, as we
have large number of training (unsupervised) samples relative to the number of model parameters,
the class-dependent Ising model outperforms the class-independent Ising model, illustrating the
benefit of moving up the hierarchy of proposed models.
The above experiments demonstrate the practical value of explicitly modeling judge dependence: when correlations are present, interaction-aware aggregation leverage the additional structure among the pool of judges and deliver consistently lower error than any conditional-independence
weighting which is based only on marginals.

10

0.90

0.85

0.80

0.75

0.800

0.775

0.750

0.725

0.700

0.675

0.650

0.700

0.675

0.650

0.625

0.600

0.575

0.550

500 750 1000 1250 1500 1750 2000 2250 2500
Sample Size

500 1000 1500 2000 2500 3000
Sample Size

200 300 400 500 600 700 800 900 1000
Sample Size

3 4 5 6
Number of Judges

3 4 5 6
Number of Judges

3 4 5 6
Number of Judges

0.900

0.875

0.850

0.825

0.800

0.775

0.750

0.78

0.76

0.74

0.72

0.70

0.68

0.700

0.675

0.650

0.625

0.600

0.575

0.550

0.525

Figure 3: Effect of varying the number of training samples (left) and number of judges (right) on
the test accuracy. Top, middle and bottom rows correspond respectively to Relevance, Toxicity
and Summarization datasets. The standard errors are of small width, although they are plotted.

### **5 Limitations and Conclusion**

While our separation results are stated in terms of the Bayes-optimal posterior under the true
generative model, in practice one must rely on computational procedures such as generalized EM
with approximate E-steps and surrogate M-steps, e.g., pseudo-likelihood. A key next step is to
extend the theory from the population Bayes rule to these algorithms: establishing conditions
under which the learned parameters and induced posteriors converge to the correct decision rule
or, at minimum, inherit the same separation from conditional-independence baselines.
Beyond parameter estimation, our framework motivates a hypothesis-testing view of LLM-as-ajudge evaluation: before fitting more expressive dependence models, practitioners can test whether
class-conditional independence is plausible by checking for residual correlations among judges after
accounting for label uncertainty, or by comparing CI and Ising/factor-model pseudo-likelihoods on
holdout items.
From a practical standpoint, the hierarchy presented in this paper provides actionable guidance:

11

one may start with CI as a cheap baseline and then move to latent-factor (low-rank) dependence
if correlations appear global or prompt-driven. When pairwise agreement patterns are strong or
class-dependent, one may escalate to class-independent or class-dependent Ising model. Simple
diagnostics—estimated coupling strength, stability across random initializations, and predictive
calibration on small labeled validation sets—can help determine the appropriate level of dependence
modeling and prevent overfitting. Such considerations may make dependence-aware aggregation a
reliable component of real-world evaluation pipelines.

### **References**

[1] CJ Adams, Daniel Borkan, Jeffrey Sorensen, Lucas Dixon, Lucy Vasserman, and nithum.
Jigsaw unintended bias in toxicity classification, 2019. URL `[https://kaggle.com/competi](https://kaggle.com/competitions/jigsaw-unintended-bias-in-toxicity-classification)`
`[tions/jigsaw-unintended-bias-in-toxicity-classification](https://kaggle.com/competitions/jigsaw-unintended-bias-in-toxicity-classification)` .

[2] Rui Ai, Yuqi Pan, David Simchi-Levi, Milind Tambe, and Haifeng Xu. Beyond majority voting:
LLM aggregation by leveraging higher-order information. _arXiv:2510.01499_, 2025.

[3] Anastasios N Angelopoulos, Stephen Bates, Clara Fannjiang, Michael I Jordan, and Tijana
Zrnic. Prediction-powered inference. _Science_, 382(6671):669–674, 2023.

[4] Anastasios N Angelopoulos, John C Duchi, and Tijana Zrnic. PPI++: Efficient predictionpowered inference. _arXiv:2311.01453_, 2023.

[5] David B Bahr and Eve Passerini. Statistical mechanics of opinion formation and collective
behavior: micro-sociology. _The_ _Journal_ _of_ _mathematical_ _sociology_, 23(1):1–27, 1998.

[6] Daniel Berend and Aryeh Kontorovich. A finite sample analysis of the naive Bayes classifier.
_J._ _Mach._ _Learn._ _Res._, 16(1):1519–1545, 2015.

[7] Bhaswar B. Bhattacharya and Sumit Mukherjee. Inference in Ising models. _Bernoulli_, 24(1):
493–525, 2018.

[8] Pierre Boyeau, Anastasios Nikolas Angelopoulos, Tianle Li, Nir Yosef, Jitendra Malik, and
Michael I. Jordan. Autoeval done right: Using synthetic data for model evaluation. In _Inter-_
_national_ _Conference_ _on_ _Machine_ _Learning_, 2025.

[9] Yi-Chun Chen, Manuel Mueller-Frank, and Mallesh Pai. The wisdom of the crowd and higherorder beliefs. In _ACM_ _Conference_ _on_ _Economics_ _and_ _Computation_, 2023.

[10] Yiqun T Chen, Sizhu Lu, Sijia Li, Moran Guo, and Shengyi Li. Efficient inference for noisy
LLM-as-a-judge evaluation. _arXiv:2601.05420_, 2026.

[11] Aida Mostafazadeh Davani, Mark D´ıaz, and Vinodkumar Prabhakaran. Dealing with disagreements: Looking beyond the majority vote in subjective annotations. _Transactions_ _of_ _the_
_Association_ _for_ _Computational_ _Linguistics_, 10:92–110, 2022.

[12] A. Philip Dawid and Allan M. Skene. Maximum likelihood estimation of observer error-rates
using the EM algorithm. _Journal_ _of_ _the_ _Royal_ _Statistical_ _Society._ _Series_ _C_ _(Applied_ _Statistics)_,
28(1):20–28, 1979.

[13] DeepSeek-AI. Deepseek-R1: Incentivizing reasoning capability in LLMs via reinforcement
learning. _arXiv:2501.12948_, 2025.

12

[14] Pinar Donmez, Guy Lebanon, and Krishnakumar Balasubramanian. Unsupervised supervised
learning I: Estimating classification and regression errors without labels. _Journal_ _of_ _Machine_
_Learning_ _Research_, 11(4), 2010.

[15] Yann Dubois, Percy Liang, and Tatsunori Hashimoto. Length-controlled alpacaeval: A simple
debiasing of automatic evaluators. In _Conference_ _on_ _Language_ _Modeling_, 2024.

[16] Sacha Friedli and Yvan Velenik. _Statistical_ _mechanics_ _of_ _lattice_ _systems:_ _a_ _concrete_ _mathe-_
_matical_ _introduction_ . Cambridge University Press, 2017.

[17] Chao Gao, Yu Lu, and Dengyong Zhou. Exact exponent in optimal rates for crowdsourcing.
In _International_ _Conference_ _on_ _Machine_ _Learning_, 2016.

[18] Shashwat Goel, Joschka Str¨uber, Ilze Amanda Auzina, Karuna K Chandra, Ponnurangam
Kumaraguru, Douwe Kiela, Ameya Prabhu, Matthias Bethge, and Jonas Geiping. Great
models think alike and this undermines AI oversight. In _International_ _Conference_ _on_ _Machine_
_Learning_, 2025.

[19] Jiawei Gu, Xuhui Jiang, Zhichao Shi, Hexiang Tan, Xuehao Zhai, Chengjin Xu, Wei Li,
Yinghan Shen, Shengjie Ma, Honghao Liu, et al. A survey on LLM-as-a-judge. _The Innovation_,
2024\.

[20] Karl Moritz Hermann, Tom´as Kocisk´y, Edward Grefenstette, Lasse Espeholt, Will Kay,
Mustafa Suleyman, and Phil Blunsom. Teaching machines to read and comprehend. In _Con-_
_ference_ _on_ _Neural_ _Information_ _Processing_ _Systems_, 2015.

[21] Holger Hoefling and Robert Tibshirani. Estimation of sparse binary pairwise Markov networks
using pseudo-likelihoods. _Journal_ _of_ _Machine_ _Learning_ _Research_, 10(4), 2009.

[22] Dirk Hovy, Taylor Berg-Kirkpatrick, Ashish Vaswani, and Eduard H. Hovy. Learning whom
to trust with MACE. In _Conference_ _of_ _the_ _North_ _American_ _Chapter_ _of_ _the_ _Association_ _of_
_Computational_ _Linguistics_, 2013.

[23] Ariel Jaffe, Ethan Fetaya, Boaz Nadler, Tingting Jiang, and Yuval Kluger. Unsupervised
ensemble learning with dependent classifiers. In _Conference_ _on_ _Artificial_ _Intelligence_ _and_
_Statistics_, 2016.

[24] Elliot Myunghoon Kim, Avi Garg, Kenny Peng, and Nikhil Garg. Correlated errors in large
language models. In _International_ _Conference_ _on_ _Machine_ _Learning_, 2025.

[25] Hyun-Chul Kim and Zoubin Ghahramani. Bayesian classifier combination. In _Conference_ _on_
_Artificial_ _Intelligence_ _and_ _Statistics_, 2012.

[26] Matth¨aus Kleindessner and Pranjal Awasthi. Crowdsourcing with arbitrary adversaries. In
_International_ _Conference_ _on_ _Machine_ _Learning_, pages 2708–2717, 2018.

[27] Chungpa Lee, Thomas Zeng, Jongwon Jeong, Jy-yong Sohn, and Kangwook Lee. How to
correctly report LLM-as-a-judge evaluations. _arXiv:2511.21140_, 2025.

[28] Dawei Li, Bohan Jiang, Liangjie Huang, Alimohammad Beigi, Chengshuai Zhao, Zhen Tan,
Amrita Bhattacharjee, Yuxuan Jiang, Canyu Chen, Tianhao Wu, Kai Shu, Lu Cheng, and
Huan Liu. From generation to judgment: Opportunities and challenges of LLM-as-a-judge. In
_Conference_ _on_ _Empirical_ _Methods_ _in_ _Natural_ _Language_ _Processing_, 2025.

13

[29] Qiang Liu, Jian Peng, and Alexander T Ihler. Variational inference for crowdsourcing. _Con-_
_ference_ _on_ _Neural_ _Information_ _Processing_ _Systems_, 2012.

[30] Yang Liu, Dan Iter, Yichong Xu, Shuohang Wang, Ruochen Xu, and Chenguang Zhu. Geval: NLG evaluation using GPT-4 with better human alignment. In _Conference_ _on_ _Empirical_
_Methods_ _in_ _Natural_ _Language_ _Processing_, 2023.

[31] Alessio Mazzetto, Dylan Sam, Andrew Park, Eli Upfal, and Stephen Bach. Semi-supervised
aggregation of dependent weak supervision sources with performance guarantees. In _Conference_
_on_ _Artificial_ _Intelligence_ _and_ _Statistics_, 2021.

[32] Blazej Miasojedow and Wojciech Rejchel. Sparse estimation in Ising model via penalized
Monte Carlo methods. _Journal_ _of_ _Machine_ _Learning_ _Research_, 19(75):1–26, 2018.

[33] OpenAI. gpt-oss-120b & gpt-oss-20b model card. _arXiv:2508.10925_, 2025.

[34] Draˇzen Prelec, H Sebastian Seung, and John McCoy. A solution to the single-question crowd
wisdom problem. _Nature_, 541(7638):532–535, 2017.

[35] Vikas C. Raykar, Shipeng Yu, Linda H. Zhao, Gerardo Hermosillo Valadez, Charles Florin,
Luca Bogoni, and Linda Moy. Learning from crowds. _Journal_ _of_ _Machine_ _Learning_ _Research_,
11:1297–1322, 2010.

[36] Utkir A Rozikov. _Gibbs_ _measures_ _in_ _biology_ _and_ _physics:_ _The_ _Potts_ _model_ . World Scientific,
2022\.

[37] Abigail See, Peter J. Liu, and Christopher D. Manning. Get to the point: Summarization
with pointer-generator networks. In _Annual_ _Meeting_ _of_ _the_ _Association_ _for_ _Computational_
_Linguistics_ _(Volume_ _1:_ _Long_ _Papers)_, 2017.

[38] Uri Shaham, Xiuyuan Cheng, Omer Dror, Ariel Jaffe, Boaz Nadler, Joseph Chang, and Yuval Kluger. A deep learning approach to unsupervised ensemble learning. In _International_
_Conference_ _on_ _Machine_ _Learning_, 2016.

[39] Jacob Steinhardt, Gregory Valiant, and Moses Charikar. Avoiding imposters and delinquents:
Adversarial crowdsourcing and peer prediction. _Advances_ _in_ _Neural_ _Information_ _Processing_
_Systems_, 29, 2016.

[40] Peter Welinder, Steve Branson, Serge J. Belongie, and Pietro Perona. The multidimensional
wisdom of crowds. In _Conference_ _on_ _Neural_ _Information_ _Processing_ _Systems_, 2010.

[41] Emily Wenger and Yoed Kenett. We’re different, we’re the same: Creative homogeneity across
LLMs. _arXiv:2501.19361_, 2025.

[42] Jacob Whitehill, Paul Ruvolo, Tingfan Wu, Jacob Bergsma, and Javier R. Movellan. Whose
vote should count more: Optimal integration of labels from labelers of unknown expertise. In
_Conference_ _on_ _Neural_ _Information_ _Processing_ _Systems_, 2009.

[43] Qi Xu, Yubai Yuan, Junhui Wang, and Annie Qu. Crowdsourcing utilizing subgroup structure
of latent factor modeling. _Journal of the American Statistical Association_, 119(546):1192–1204,
2024\.

14

[44] Yi Yang, Wen-tau Yih, and Christopher Meek. WikiQA: A challenge dataset for open-domain
question answering. In _Conference_ _on_ _Empirical_ _Methods_ _in_ _Natural_ _Language_ _Processing_,
2015\.

[45] Lianmin Zheng, Wei-Lin Chiang, Ying Sheng, Siyuan Zhuang, Zhanghao Wu, Yonghao Zhuang,
Zi Lin, Zhuohan Li, Dacheng Li, Eric Xing, Hao Zhang, Joseph E. Gonzalez, and Ion Stoica.
Judging LLM-as-a-judge with MT-bench and chatbot arena. In _Conference_ _on_ _Neural_ _Infor-_
_mation_ _Processing_ _Systems_ _(Datasets_ _and_ _Benchmarks_ _Track)_, 2023.

15

### Appendix **A Related Works**

The LLM-as-a-judge literature uses LLMs to approximate human preferences in open-ended evaluation, including MT-Bench/Chatbot Arena [45] and prompt-based evaluators such as G-Eval [30],
as well as benchmark suites like AlpacaEval and debiasing methods for judge preferences (e.g.,
length control) [15, 28]. See, for example, Gu et al. [19] for a survey and Chen et al. [10], Lee et al.

[27] for some recent works.
In the context of binary classification, however, label aggregation has been carried out using
majority voting and its weighted variants much before their use in LLM-as-a-judge applications.
Our focus is on the case of unsupervised label aggregation in which the unknown true label is
treated as a latent variable and EM algorithm is used to infer it. The approach was proposed
by Dawid and Skene [12] and analyzed by Berend and Kontorovich [6], Donmez et al. [14], Gao
et al. [17], Raykar et al. [35]. A large literature on _crowdsourcing_ extends this template by enriching
the annotator/item structure while typically retaining conditional independence of votes given
latent variables, e.g., modeling annotator expertise and item difficulty (GLAD) [11, 42, 43], multidimensional annotator effects [40], and incorporating item features jointly with label aggregation
(also called as “learning from crowds”) [35]. Bayesian variants and alternatives include Bayesian
classifier combination [25] and models designed to detect spammers/adversaries such as MACE [22].
Motivated by economics and customer study literatures [9, 34], recently Ai et al. [2] study
LLM aggregation beyond majority vote by proposing _optimal_ _weight_ using first-order statistics and
_Inverse_ _Surprising_ _Popularity_ using second-order cross-agent conditional response statistics with
theoretical improvements and empirical gains. But their main guarantees effectively assume oraclequality second-order information _P_ ( _Ji | Jj_ ) for Judges _i_ and _j_ (treated as “accurate” before finitesample estimation), which can be sample-hungry to estimate and can be brittle under distribution
shift or latent-difficulty confounding that changes apparent correlations. Furthermore, they assume
the judge labels are conditionally independent given the true label.
While the aforementioned works document biases and variance in LLM judging, they typically
aggregate multiple judge calls using independence-based heuristics; our focus is on explicitly modeling and exploiting _dependence_ among judges (e.g., shared prompts or shared failure modes) via
Ising structure.
Initial steps towards handling dependencies have been taken by Jaffe et al. [23] and Shaham
et al. [38]. In particular, these works study the case of hierarchically dependent judges/annotators, a relaxation of fully conditionally independent judges. While appropriate for certain crowdsourcing applications (e.g., workers clustered by source or organization), this assumption is poorly
aligned with LLM-as-a-judge settings: dependencies among LLM judges are rarely tree-structured
or nested, and instead arise from overlapping pretraining data, shared architectures, and reused
prompting templates that induce _dense,_ _non-hierarchical_ correlations and shared failure modes.
As a result, hierarchical-dependence models can miss the dominant correlation patterns in practice
and provide limited guidance for correcting over-counted agreement in modern LLM evaluation
pipelines. Mazzetto et al. [31] studied a setting where not all the judges are conditionally independent, however a subset of them are. Their approach, however, is fundamentally semi-supervised

16

meaning that they required some amount of labeled data. We also remark that in the fullysupervised setting, several works [26, 39] considered adversarial annotators which maybe arbitrarily
correlated. Compared to these works, our focus is in the purely unsupervised setting.
Finally, we remark that recent works have used additional human (supervised) annotated labels
to improve the unknown label inference via the framework of prediction powered inference; see,
for example [3, 4, 8]. While we work under the purely unsupervised setting, we remark that our
proposed models integrate seamlessly with the aforementioned framework.

### **B Motivating Example**

Consider three LLM annotators producing binary votes. Annotators 1 and 3 share substantial
training data and prompt templates, so their outputs are highly correlated (they tend to agree,
including on shared mistakes). Annotator 2 uses a different prompt style and often behaves differently from the other two. These agreement/disagreement patterns are driven by shared modeling
choices and therefore persist _regardless_ _of_ _the_ _true_ _class_ _label_ . Consequently, certain vote patterns
primarily reflect shared failure modes rather than independent evidence.
Under CI, methods such as the Dawid-Skene method, treats annotator votes as independent
given _Y_, and therefore interprets agreement as multiple independent pieces of evidence. In contrast,
an Ising model explicitly represents dependencies via pairwise interactions, allowing the posterior
to correctly discount redundant agreement and to recognize “unlikely” vote configurations created
by structural correlations.
We now give a concrete population example in which the a CI-predictor predicts the opposite
label from the Bayes-optimal predictor under a class-independent Ising model, _even_ _though_ _CI_ _is_
_given_ _the_ _correct_ _one-dimensional_ _marginals_ .
We now consider a single item ( _n_ = 1) with label _Y_ _∈{_ 0 _,_ 1 _}_ and three annotators

_J_ = ( _J_ 1 _, J_ 2 _, J_ 3) _∈{_ 0 _,_ 1 _}_ [3] _,_

with a uniform prior P( _Y_ = 1) = P( _Y_ = 0) = 2 [1] [.] [We] [interpret] _[J][k]_ [=] [1] [as] [annotator] _[k]_ [voting] [for]

class 1 and _Jk_ = 0 as voting for class 0.
We now consider the case when the judge labels are generated from the _class-independent_
_coupling_ Ising model

3
1 - P( _J_ _| Y_ = _y_ ) = [exp]
_Z_ [(] _[y]_ [)]

_h_ [(] _k_ _[y]_ [)] _[J][k]_ [ +] [1]

2

_k_ =1

2

-

_Wkℓ_ _JkJℓ_ _,_ _y_ _∈{_ 0 _,_ 1 _},_ (9)

_k_ = _ℓ_

where the coupling matrix _W_ is shared across classes (capturing label-independent dependence),
and only the fields _h_ [(] _[y]_ [)] depend on _y_ . In this numerical instance,





_W_ =

 0 _−_ 2 _._ 7496 4 _._ 4583

 _−_ 2 _._ 7496 0 _−_ 4 _._ 8249
4 _._ 4583 _−_ 4 _._ 8249 0

 _,_

_h_ [(0)] = ( _−_ 1 _._ 7447 _,_ 2 _._ 2991 _,_ 3 _._ 5085) _,_

_h_ [(1)] = ( _−_ 2 _._ 0094 _,_ 0 _._ 1721 _,_ _−_ 2 _._ 7597) _._

Here _W_ 13 _>_ 0 encourages annotators 1 and 3 to co-activate, while _W_ 12 _, W_ 23 _\<_ 0 discourage annotator 2 from co-activating with annotators 1 and 3; this encodes the “ _{_ 1 _,_ 3 _}_ similar, 2 different”
structure.

17

Since there are only 2 [3] = 8 vote patterns, we can normalize (9) exactly by enumeration. The
resulting conditional distributions are:

( _J_ 1 _, J_ 2 _, J_ 3) P( _J_ _| Y_ = 0) P( _J_ _| Y_ = 1)
(0 _,_ 0 _,_ 0) 0 _._ 00181 0 _._ 3196
(0 _,_ 0 _,_ 1) 0 _._ 0603 0 _._ 0202
(0 _,_ 1 _,_ 0) 0 _._ 0180 0 _._ 3796
(0 _,_ 1 _,_ 1) 0 _._ 00483 1 _._ 93 _×_ 10 _[−]_ [4]

(1 _,_ 0 _,_ 0) 3 _._ 16 _×_ 10 _[−]_ [4] 0 _._ 0428
(1 _,_ 0 _,_ 1) 0 _._ 9099 0 _._ 2342
(1 _,_ 1 _,_ 0) 2 _._ 01 _×_ 10 _[−]_ [4] 0 _._ 00325
(1 _,_ 1 _,_ 1) 0 _._ 00465 1 _._ 43 _×_ 10 _[−]_ [4]

We first calculate the Bayes-optimal posterior under the true Ising model. Consider the observed
votes
_J_ = (0 _,_ 1 _,_ 1) _._

From the table,
P( _J_ _| Y_ = 0) = 0 _._ 0048253 _,_ P( _J_ _| Y_ = 1) = 0 _._ 0001929 _._

With a uniform prior,

P( _J_ _| Y_ = 1) 1 _._ 93 _×_ 10 _[−]_ [4]
P( _Y_ = 1 _| J_ ) = _[≈]_ [0] _[.]_ [038] _[.]_
P( _J_ _| Y_ = 0) + P( _J_ _| Y_ = 1) _[≈]_ 4 _._ 83 _×_ 10 _[−]_ [3] + 1 _._ 93 _×_ 10 _[−]_ [4]

Thus the Bayes-optimal prediction is _Y_ = 0.
Next we show that a CI-predictor, i.e., assuming conditional independence across judges predicts
the opposite label. Let
_πk_ [(] _[y]_ [)] := P( _Jk_ = 1 _| Y_ = _y_ )

denote the _true_ class-conditional one-dimensional marginals implied by the Ising model (9). From
the table (summing over the other coordinates),

( _π_ 1 [(0)] _[, π]_ 2 [(0)] _[, π]_ 3 [(0)][)] _[ ≈]_ [(0] _[.]_ [9150] _[,]_ [0] _[.]_ [0277] _[,]_ [0] _[.]_ [9797)] _[,]_ ( _π_ 1 [(1)] _[, π]_ 2 [(1)] _[, π]_ 3 [(1)][)] _[ ≈]_ [(0] _[.]_ [2804] _[,]_ [0] _[.]_ [3832] _[,]_ [0] _[.]_ [2548)] _[.]_

The CI likelihood replaces the true joint distribution by the product of these marginals:

PCI( _J_ _| Y_ = _y_ ) =

3

_k_ =1

- _πk_ [(] _[y]_ [)] - _Jk_ �1 _−_ _πk_ [(] _[y]_ [)] �1 _−Jk_ _._ (10)

For _J_ = (0 _,_ 1 _,_ 1),

PCI( _J_ _| Y_ = 0) = (1 _−_ _π_ 1 [(0)][)] _[ π]_ 2 [(0)] _π_ 3 [(0)] _≈_ 0 _._ 00230 _,_ PCI( _J_ _| Y_ = 1) = (1 _−_ _π_ 1 [(1)][)] _[ π]_ 2 [(1)] _π_ 3 [(1)] _≈_ 0 _._ 0702 _._

Therefore, with the same uniform prior,

PCI( _J_ _| Y_ = 1)
PCI( _Y_ = 1 _| J_ ) =
PCI( _J_ _| Y_ = 0) + PCI( _J_ _| Y_ = 1) _[≈]_ [0] _[.]_ [968] _[,]_

so the CI-predictor generates _Y_ = 1 with high confidence.
This example isolates a purely _model-misspecification_ effect: CI is fed the correct class-conditional
marginals ( _πk_ [(] _[y]_ [)][),] [but] [it] [still] [fails] [because] [it] [assumes] [independence.] [The] [true] [Ising] [model] [assigns]

18

extremely low probability to _J_ = (0 _,_ 1 _,_ 1) under _Y_ = 1 (about 1 _._ 9 _×_ 10 _[−]_ [4] ), reflecting the fact that
the vote pattern is structurally inconsistent with the label-independent correlation pattern encoded
by _W_ . CI cannot represent this structural constraint and therefore overestimates P( _J_ _| Y_ = 1) by
orders of magnitude, leading to the wrong posterior label.
If dependence patterns also differ by class (i.e., _W_ [(1)] = _W_ [(0)] ), then the Bayes log-odds contains
quadratic terms _JiJj_ and the same phenomenon can be even more pronounced. For example, with









_W_ [(0)] =

 0 _−_ 2 _._ 4445 2 _._ 4553

 _−_ 2 _._ 4445 0 _−_ 2 _._ 9206
2 _._ 4553 _−_ 2 _._ 9206 0

 _,_ _W_ [(1)] =

 0 _−_ 3 _._ 3637 3 _._ 0718

 _−_ 3 _._ 3637 0 _−_ 0 _._ 0677
3 _._ 0718 _−_ 0 _._ 0677 0

 _,_

_h_ [(0)] = (2 _._ 7369 _,_ 1 _._ 3602 _,_ 1 _._ 9559) _,_ _h_ [(1)] = ( _−_ 2 _._ 5484 _,_ _−_ 2 _._ 2580 _,_ _−_ 0 _._ 9266) _,_

and P( _Y_ = 1) = [1] [the] [observation] _[J]_ [= (1] _[,]_ [ 1] _[,]_ [ 0)] [satisfies]

2 [,]

P( _J_ _| Y_ = 0) _≈_ 0 _._ 00393 _,_ P( _J_ _| Y_ = 1) _≈_ 1 _._ 24 _×_ 10 _[−]_ [4] _,_

so Bayes predicts _Y_ = 0 (posterior _≈_ 0 _._ 031), whereas CI built from the correct marginals yields
PCI( _Y_ = 1 _|_ _J_ ) _≈_ 0 _._ 957 and predicts _Y_ = 1. This illustrates the same qualitative failure mode
when class information appears directly in correlation differences.

### **C Additional Discussion on the Models**

**C.1** **Conditionally** **Independent** **Model** **with** **Asymmetric** **Errors**

For the sake of completeness, we introduce the conditionally independent model which assume
asymmetric errors. We assume that, conditional on _Yi_, judges act independently and their accuracies do not depend on the item index _i_ . For each judge _j_ _∈{_ 1 _, . . ., K}_ define the _sensitivity_ and
_specificity_
_αj_ := P( _Jij_ = 1 _| Yi_ = 1) _,_ _βj_ := P( _Jij_ = 0 _| Yi_ = 0) _._

Equivalently, the false-negative and false-positive rates are

P( _Jij_ = 0 _| Yi_ = 1) = 1 _−_ _αj,_ P( _Jij_ = 1 _| Yi_ = 0) = 1 _−_ _βj._

Let _π_ := P( _Yi_ = 1) denote the class prior. The generative model is

_Yi_ _∼_ Bernoulli( _π_ ) _,_ _Jij_ _|_ ( _Yi_ = _y_ ) ind _∼_ Bernoulli� _αj_ **1** _{y_ = 1 _}_ + (1 _−_ _βj_ ) **1** _{y_ = 0 _}_ - _,_

independently across judges _j_ and items _i_ given the parameters. When parameters are unknown,
a convenient conjugate choice is independent Beta priors

_αj_ _∼_ Beta( _a_ 1 _j, b_ 1 _j_ ) _,_ _βj_ _∼_ Beta( _a_ 0 _j, b_ 0 _j_ ) _,_ _π_ _∼_ Beta( _c, d_ ) _,_

with density proportional to _p_ _[a][−]_ [1] (1 _−_ _p_ ) _[b][−]_ [1] on \[0 _,_ 1\]. The next result gives the _exact_ posterior
log-odds under CI when ( _α, β, π_ ) are known (or when a plug-in estimate is used). The posterior
log-odds satisfies

- _αj_
  _Jij_ log + (1 _−_ _Jij_ ) log [1] _[ −]_ _[α][j]_
  1 _−_ _βj_ _βj_

19

[= 1] _[ |][ J][i]_ [)] _π_
log [P(] _[Y][i]_

P( _Yi_ = 0 _| Ji_ ) [= log] 1 _−_ _π_ [+]

_K_

_j_ =1

_._ (11)

Equivalently, (11) can be written as an affine (weighted-vote) score:

_K_

log [1] _[ −]_ _[α][j]_

_βj_

_j_ =1

_._
_βj_

log [P(] _[Y][i]_ [= 1] _[ |][ J][i]_ [)]

P( _Yi_ = 0 _| Ji_ ) [=] _[ b]_ [ +]

_K_

- _αjβj_ _π_

_wj Jij,_ _wj_ = log _b_ = log
(1 _−_ _αj_ )(1 _−_ _βj_ ) _[,]_ 1 _−_ _π_ [+]
_j_ =1

(12)

Hence the Bayes-optimal CI decision rule is the _weighted_ _majority_ _vote_, given by




_K_

_wjJij_ _≥_ 0

_j_ =1




 _[.]_

_Y_ ˆ _i_ = **1**

 _[b]_ [ +]

The weight _wj_ is positive iff _αj_ + _βj_ _>_ 1, i.e., judge _j_ is better than random guessing; it is negative
for adversarial judges. In the _symmetric_ special case _αj_ = _βj_ = _pj_, one obtains _wj_ = 2 log 1 _−pjpj_
and an intercept depending on _π_, recovering the familiar weighted-majority log-odds form under
conditional independence.

**C.2** **Relation** **to** **LDA** **and** **QDA**

The separation between conditional-independence aggregation and class-dependent Ising aggregation is closely analogous to the classical gap between _linear_ and _quadratic_ discriminant analysis in
Gaussian classification. In the Gaussian setting, the Bayes log-likelihood ratio for _x ∈_ R _[d]_ takes the
form

log [P(] _[x][ |][ Y]_ [= 1)]

P( _x | Y_ = 0) [=] _[ x][⊤][Ax]_ [ +] _[ b][⊤][x]_ [ +][ c] _[,]_

where c is constant and the quadratic term _x_ _[⊤]_ _Ax_ vanishes exactly when the class covariances coincide (Σ0 = Σ1), yielding LDA; otherwise QDA is optimal and the decision boundary is quadratic.
In our discrete vote setting with _J_ _∈{_ 0 _,_ 1 _}_ _[K]_, the class-dependent Ising model yields an _exactly_
_analogous_ decomposition:

∆ _Wjk JjJk,_
1 _≤j\<k≤K_

_[|][ Y]_ [= 1)]
log [P(] _[J]_ [+]

P( _J_ _| Y_ = 0) [= ∆] _[Z]_

_K_

-

∆ _hj Jj_ +
_j_ =1 1 _≤j\<k_

so the Bayes decision boundary is quadratic in the votes whenever _W_ [(1)] = _W_ [(0)], and it collapses
to a linear weighted vote precisely when couplings are shared across classes ( _W_ [(1)] = _W_ [(0)] ). From
this perspective, the Ising coupling matrix _W_ plays a role analogous to _second-order_ _structure_
(covariance/precision) in Gaussian models, and ∆ _Z_ = _−_ log _Z_ [(1)] + log _Z_ [(0)] is the discrete analog of
the log-determinant term that appears in QDA.
The analogy is not merely formal: both frameworks say that when class information lives in
_dependence_ _structure_ rather than only in _marginals_, linear/CI rules can be fundamentally misspecified. In particular, just as QDA can separate classes even when means coincide but covariances
differ, a class-dependent Ising model can separate classes even when one-dimensional marginals
are uninformative, provided the pairwise interaction patterns differ across classes. This is exactly
the mechanism behind our separation results (proved later in Section 3): CI uses only products
of marginals (a linear log-odds in _J_ ), so it cannot exploit label-dependent correlations encoded by
∆ _W_ and can remain strictly suboptimal. At the same time, there are important differences from
the Gaussian discriminant analysis problem. In particular, the statistical/computational trade-off
is sharper for Ising models because likelihood evaluation involves partition functions, motivating
pseudo-likelihood/approximate inference in EM. We leave a detailed examination of this tradeoff
for future work.

20

**C.3** **Relation** **to** **Factor** **Model**

While our focus so far has been on Ising models for capturing dependency, yet another class of
models widely used to capture dependencies are factor models. In the context of unsupervised
aggregation, Whitehill et al. [42] and Xu et al. [43] study factor models to handle potential latent
dependencies between the annotators. It is hence natural to explore the connections between the
two classes of models. Below, we show that such latent-factor models are approximate special cases
of the class-independent Ising models. To the best of our knowledge, this connection has not been
observed in the literature despite a considerable amount of work on both models.

**Proposition** **1** (Latent-factor _⇒_ low-rank class-independent Ising couplings to second order) **.** _Fix_
_K, r_ _∈_ N _and_ _let_ _J_ = ( _J_ 1 _, . . ., JK_ ) _∈{_ 0 _,_ 1 _}_ _[K]_ _._ _Let_ _σ_ ( _t_ ) = (1 + _e_ _[−][t]_ ) _[−]_ [1] _and_ _define_ _ηj_ ( _y_ ) := _ajy_ + _bj_
_for_ _y_ _∈{_ 0 _,_ 1 _}._ _Let_ _Z_ _∼N_ (0 _, Ir_ ) _be_ _independent_ _of_ _Y_ _∼_ Bernoulli( _π_ ) _,_ _and_ _assume_ _that_ _conditional_
_on_ ( _Y_ = _y, Z_ = _z_ ) _,_

_Jj_ _|_ ( _Y_ = _y, Z_ = _z_ ) _∼_ Bernoulli� _σ_ ( _ηj_ ( _y_ ) + _λ_ _[⊤]_ _j_ _[z]_ [)] - _,_ _j_ = 1 _, . . ., K,_

_independently_ _over_ _j._ _Let_ _ε_ _>_ 0 _and_ _define_ _the_ _loadings_ _as_ _λj_ = _ε_ _λ_ [˜] _j_ _with_ _fixed_ _λ_ [˜] _j_ _∈_ R _[r]_ _satisfying_
max _j ∥λ_ [˜] _j∥≤_ _L._ _Let_ Λ [˜] _∈_ R _[K][×][r]_ _have_ _rows_ _λ_ [˜] _[⊤]_ _j_ _[so]_ _[that]_ [Λ] [=] _[ε]_ [˜Λ] _[.]_ _[For]_ _[a]_ _[fixed]_ _[class]_ _[y]_ _[∈{]_ [0] _[,]_ [ 1] _[}]_ _[write]_
_ηj_ = _ηj_ ( _y_ ) _and_ _pj_ := _σ_ ( _ηj_ ) _._
_Then_ _there_ _exist_ _Cy_ ( _ε_ ) _independent_ _of_ _J_ _and_ _a_ _remainder_ _Ry_ ( _J_ ; _ε_ ) _such_ _that,_ _for_ _all_ _ε_ _small_
_enough,_

log P _ε_ ( _J_ _| Y_ = _y_ ) = _Cy_ ( _ε_ ) +

_K_

_h_ [(] _j_ _[y]_ [)][(] _[ε]_ [)] _[ J][j]_ [+] [1]

2

_j_ =1

2

( _λ_ _[⊤]_ _j_ _[λ][k]_ [)] _[ J][j][J][k]_ [+] _[ R][y]_ [(] _[J]_ [;] _[ ε]_ [)] _[,]_ (13)
_j_ = _k_

_where_ _the_ _(class-dependent)_ _fields_ _admit_ _the_ _explicit_ _second-order_ _expansion_

_h_ [(] _j_ _[y]_ [)][(] _[ε]_ [) =] _[ η][j]_ [+] - 12 _[−]_ _[p][j]_ - _∥λj∥_ [2] _−_ - _pk λ_ _[⊤]_ _j_ _[λ][k][,]_ _j_ = 1 _, . . ., K,_ (14)

_k_ = _j_

_and_ _the_ _remainder_ _is_ _uniformly_ _bounded_ _as_

_K_

- _∥λ_ [˜] _j∥_ [3] + _C ε_ [4][�] - _[K]_

_j_ =1 _j_ =1

_K_

```
_J∈{_ sup0 _,_ 1 _}_ _[K]_ _[|][R][y]_ [(] _[J]_ [;] _[ ε]_ [)] _[|]_ _[≤]_ _[C ε]_ [3]
```

- _[K]_ _∥λ_ [˜] _j∥_ [2][�][2] _≤_ _C_ _[′]_ _ε_ [3][�] max _∥λ_ [˜] _j∥_ - - _[K]_

_j_
_j_ =1 _j_ =1

- _∥λ_ [˜] _j∥_ [2] + _C ε_ [4] _∥_ Λ [˜] _∥_ [4] _F_ _[,]_

_j_ =1

(15)

_for_ _constants_ _C, C_ _[′]_ _>_ 0 _depending_ _only_ _on_ _r_ _and_ _{ηj_ ( _y_ ) _}j≤K_ _(in_ _particular,_ _not_ _on_ _J_ _or_ _ε)._
_In_ _particular,_ _the_ _second-order_ _truncation_ _is_ _a_ _quadratic_ _binary_ _MRF_ _with_ _pairwise_ _couplings_
_given by the off-diagonal entries of the rank-≤_ _r_ _matrix_ ΛΛ _[⊤]_ _, since_ (ΛΛ _[⊤]_ ) _jk_ = _λ_ _[⊤]_ _j_ _[λ][k][).]_ _[The diagonal]_
_entries_ _of_ ΛΛ _[⊤]_ _correspond_ _to_ _Jj_ [2] [=] _[ J][j]_ _[terms]_ _[and]_ _[may]_ _[be]_ _[absorbed]_ _[into]_ _[the]_ _[fields.]_

_Proof._ Fix _y_ _∈{_ 0 _,_ 1 _}_ and abbreviate _ηj_ = _ηj_ ( _y_ ) and _pj_ = _σ_ ( _ηj_ ). Write _g_ ( _t_ ) := log(1 + _e_ _[t]_ ) so that
_g_ _[′]_ ( _t_ ) = _σ_ ( _t_ ), _g_ _[′′]_ ( _t_ ) = _σ_ ( _t_ )(1 _−_ _σ_ ( _t_ )), and

_g_ [(3)] ( _t_ ) = _σ_ ( _t_ )(1 _−_ _σ_ ( _t_ ))(1 _−_ 2 _σ_ ( _t_ )) _,_ sup _|g_ [(3)] ( _t_ ) _| ≤_ [1]
_t∈_ R 4 _[.]_

We first start with the following integral representation. Conditional on _Z_ = _z_, we have that

P _ε_ ( _J_ _| Y_ = _y, Z_ = _z_ ) =

_K_

- _σ_ ( _ηj_ + _λ_ _[⊤]_ _j_ _[z]_ [)] _[J][j]_ [�] 1 _−_ _σ_ ( _ηj_ + _λ_ _[⊤]_ _j_ _[z]_ [)] �1 _−Jj_ _._

_j_ =1

21

Hence, marginalizing over _Z_, we obtain

```
              P _ε_ ( _J_ _| Y_ = _y_ ) =          - _Sε_ ( _z_ )� _ϕr_ ( _z_ ) _dz,_
```

R _[r]_ [ exp]

where _ϕr_ is the standard _r_ -variate Gaussian density and

_Sε_ ( _z_ ) :=

_K_

_j_ =1

- _Jj_ ( _ηj_ + _λ_ _[⊤]_ _j_ _[z]_ [)] _[ −]_ _[g]_ [(] _[η][j]_ [+] _[ λ][⊤]_ _j_ _[z]_ [)] _._

We now do a second-order Taylor expansion in _λ_ _[⊤]_ _j_ _[z]_ [.] [By] [Taylor’s] [theorem,] [for] [each] _[ℓ]_ _[∈]_ [R][,]

[+] _[ θℓ]_ [)]

[1] 2 _[g][′′]_ [(] _[η][j]_ [)] _[ ℓ]_ [2][ +] _[ R][j]_ [(] _[ℓ]_ [)] _[,]_ _Rj_ ( _ℓ_ ) = _[g]_ [(3)][(] _[η][j]_

_g_ ( _ηj_ + _ℓ_ ) = _g_ ( _ηj_ ) + _pj ℓ_ + [1]

_[j]_

_ℓ_ [3] (16)
6

for some _θ_ = _θ_ ( _ℓ_ ) _∈_ (0 _,_ 1). Therefore

_|Rj_ ( _ℓ_ ) _| ≤_ [sup] _[t][ |][g]_ [(3)][(] _[t]_ [)] _[|]_

(17)
24 _[|][ℓ][|]_ [3] _[.]_

_[g]_ [(] _[t]_ [)] _[|]_

_|ℓ|_ [3] _≤_ [1]
6

Applying (16) with _ℓ_ = _λ_ _[⊤]_ _j_ _[z]_ [yields] [the] [exact] [decomposition]

_Sε_ ( _z_ ) = _A_ ( _J_ ) + _u_ _[⊤]_ _z −_ 2 [1] _[z][⊤][Mz]_ [ +] _[ R]_ [(] _[z]_ [)] _[,]_

where

_A_ ( _J_ ) :=

_K_

_j_ =1

- _Jjηj_ _−_ _g_ ( _ηj_ )� _,_ _u_ :=

_K_

_g_ _[′′]_ ( _ηj_ ) _λjλ_ _[⊤]_ _j_ _[∈]_ [R] _[r][×][r][,]_
_j_ =1

_K_

( _Jj_ _−_ _pj_ ) _λj_ _∈_ R _[r]_ _,_ _M_ :=

_j_ =1

and the remainder is

By (17), we have that

_R_ ( _z_ ) := _−_

_K_

_Rj_ ( _λ_ _[⊤]_ _j_ _[z]_ [)] _[.]_
_j_ =1

_K_

[1]

24 _[∥][z][∥]_ [3]

_|R_ ( _z_ ) _| ≤_ [1]

24

_K_

- _|λ_ _[⊤]_ _j_ _[z][|]_ [3] _[≤]_ [1]

_j_ =1

- _∥λj∥_ [3] _._ (18)

_j_ =1

Combining with _ϕr_ ( _z_ ) _∝_ _e_ _[−∥][z][∥]_ [2] _[/]_ [2] gives the following integral representation:

```
        P _ε_ ( _J_ _| Y_ = _y_ ) = (2 _π_ ) _[−][r/]_ [2] _e_ _[A]_ [(] _[J]_ [)]
```

[1] [+] _[ M]_ [)] _[z]_ _e_ _[R]_ [(] _[z]_ [)] _dz._

2 _[z][⊤]_ [(] _[I]_

_u_ _[⊤]_ _z −_ [1]

2

R _[r]_ [ exp]

We now derive an exact Gaussian integral for the quadratic part. For _ε_ small enough, _∥M_ _∥_ _\<_ 1
(indeed _∥M_ _∥≤_ [1] - _[∥][λ][j][∥]_ [2][)] [so] _[I]_ [+] _[ M]_ _[≻]_ [0.] [Let] [Σ := (] _[I]_ [+] _[ M]_ [)] _[−]_ [1] [and] _[µ]_ [ := Σ] _[u]_ [.] [Then]

_∥≤_ [1] 4 - _j_ _[∥][λ][j][∥]_ [2][)] [so] _[I]_ [+] _[ M]_ _[≻]_ [0.] [Let] [Σ := (] _[I]_ [+] _[ M]_ [)] _[−]_ [1] [and] _[µ]_ [ := Σ] _[u]_ [.] [Then]

[1] [+] _[ M]_ [)] _[z]_ - _dz_ = (2 _π_ ) _[r/]_ [2] det( _I_ + _M_ ) _[−]_ [1] _[/]_ [2] exp� 1 - _,_

2 _[z][⊤]_ [(] _[I]_ 2 _[u][⊤]_ [Σ] _[u]_

_u_ _[⊤]_ _z −_ [1]

2

R _[r]_ [ exp]

and hence

log P _ε_ ( _J_ _| Y_ = _y_ ) = _A_ ( _J_ ) _−_ [1]

[1] [+] _[ M]_ [) +] [1]

2 [log det(] _[I]_ 2

[1] (19)

2 _[u][⊤]_ [Σ] _[u]_ [ + ∆(] _[J]_ [;] _[ ε]_ [)] _[,]_

22

where
∆( _J_ ; _ε_ ) := log E _Z∼N_ ( _µ,_ Σ)� _e_ _[R]_ [(] _[Z]_ [)][�] _._

We now proceed with bounding ∆( _J_ ; _ε_ ) from (19). Define _B_ 2 := [�] _j_ _[K]_ =1 _[∥][λ]_ [˜] _[j][∥]_ [2] [and] _[B]_ [3] [:=]

- _Kj_ =1 _[∥][λ]_ [˜] _[j][∥]_ [3][.] [Since] _[λ][j]_ [=] _[ ε][λ]_ [˜] _[j]_ [,] [(18)] [implies]

_|R_ ( _z_ ) _| ≤_ [1]

24 _[ε]_ [3] _[ B]_ [3] _[ ∥][z][∥]_ [3] _[.]_

Also, _u_ = _O_ ( _ε_ ) uniformly in _J_ because _|Jj_ _−_ _pj| ≤_ 1 gives

_K_

- _∥λ_ [˜] _j∥._

_j_ =1

_∥u∥≤_

_K_

- _∥λj∥_ = _ε_

_j_ =1

Moreover, _∥M_ _∥_ = _O_ ( _ε_ [2] ) uniformly in _J_ (in fact _M_ does not depend on _J_ ), so for _ε_ small the
eigenvalues of Σ = ( _I_ + _M_ ) _[−]_ [1] are bounded above and below by absolute constants, and _∥µ∥_ =
_∥_ Σ _u∥_ = _O_ ( _ε_ ) uniformly in _J_ .
Let _Z_ _∼N_ ( _µ,_ Σ) and set _R_ := _ε_ _[−]_ [1] _[/]_ [2] . Split

E\[ _e_ _[R]_ [(] _[Z]_ [)] \] = E� _e_ _[R]_ [(] _[Z]_ [)] **1** _{∥Z∥≤R}_ - + E� _e_ _[R]_ [(] _[Z]_ [)] **1** _{∥Z∥>R}_ - _._

On _{∥Z∥≤_ _R}_ we have _|R_ ( _Z_ ) _|_ _≤_ 241 _[ε]_ [3] _[B]_ [3] _[R]_ [3] [=] 241 _[ε]_ [3] _[/]_ [2] _[B]_ [3][,] [which] [is] _[≤]_ [1] _[/]_ [2] [for] _[ε]_ [small] [(since] _[B]_ [3] [is]
fixed). Therefore _|e_ _[R]_ [(] _[Z]_ [)] _−_ 1 _| ≤_ 2 _|R_ ( _Z_ ) _|_ on _{∥Z∥≤_ _R}_ and

E� _e_ _[R]_ [(] _[Z]_ [)] **1** _{∥Z∥≤R}_ - _−_ P( _∥Z∥≤_ _R_ ) _≤_ 2 E� _|R_ ( _Z_ ) _|_ - _≤_ _C ε_ [3] _B_ 3 _,_
��� ���

using E _∥Z∥_ [3] _< ∞_ (uniformly in _J_ ) and the bound on _|R|_ .
For the tail term, one can use a quadratic-envelope bound ensuring _e_ _[R]_ [(] _[Z]_ [)] is at most Gaussianquadratic in _Z_ (because _g_ _[′′]_ ( _·_ ) _≤_ 1 _/_ 4), yielding _e_ _[R]_ [(] _[Z]_ [)] _≤_ exp( _c ε_ [2] _B_ 2 _∥Z∥_ [2] ) for a constant _c_ depending
only on _{ηj}_ . Since _Z_ is Gaussian with covariance uniformly comparable to _Ir_,

E� _e_ _[R]_ [(] _[Z]_ [)] **1** _{∥Z∥>R}_ - _≤_ E� exp( _c ε_ [2] _B_ 2 _∥Z∥_ [2] ) **1** _{∥Z∥>R}_ - _≤_ exp( _−c_ _[′]_ _/ε_ )

for some _c_ _[′]_ _>_ 0 and all _ε_ small enough (uniformly in _J_ ).
Combining these bounds shows that

E\[ _e_ _[R]_ [(] _[Z]_ [)] \] = 1 + _O_ ( _ε_ [3] _B_ 3) uniformly in _J,_

and hence, for _ε_ small enough so that _|_ E\[ _e_ _[R]_ [(] _[Z]_ [)] \] _−_ 1 _| ≤_ 1 _/_ 2,

_|_ ∆( _J_ ; _ε_ ) _|_ = �� log E\[ _eR_ ( _Z_ )\]�� _≤_ 2 ��E\[ _eR_ ( _Z_ )\] _−_ 1�� _≤_ _C ε_ 3 _B_ 3 _,_

uniformly over _J_ .
Next, we expand the quadratic Gaussian terms. Since _∥M_ _∥_ = _O_ ( _ε_ [2] _B_ 2), we have

Σ = ( _I_ + _M_ ) _[−]_ [1] = _I_ + _O_ ( _ε_ [2] _B_ 2) _,_ log det( _I_ + _M_ ) = tr( _M_ ) + _O_ ( _ε_ [4] _B_ 2 [2][)] _[.]_

Therefore

1 [1]
2 _[u][⊤]_ [Σ] _[u]_ [ =] 2

[1] 2 _[u][⊤][u]_ [ +] _[ O]_ [(] _[ε]_ [4] _[B]_ 2 [2][)] _[,]_ _−_ [1] 2

[1] 2 [log det(] _[I]_ [+] _[ M]_ [) =] _[ C]_ [(] _[J]_ [) +] _[ O]_ [(] _[ε]_ [4] _[B]_ 2 [2][)] _[,]_

23

where _C_ ( _J_ ) is constant in _J_ and the _J_ -independent pieces are absorbed into _Cy_ ( _ε_ ). Plugging into
(19) yields

[1]

2 _[u][⊤][u]_ [ +] _[ R][y]_ [(] _[J]_ [;] _[ ε]_ [)] _[,]_

log P _ε_ ( _J_ _| Y_ = _y_ ) = _Cy_ ( _ε_ ) +

_K_

- _ηjJj_ + [1] 2

_j_ =1

with
sup _|Ry_ ( _J_ ; _ε_ ) _| ≤_ _Cε_ [3] _B_ 3 + _Cε_ [4] _B_ 2 [2] _[.]_
_J_

It remains now to extract the fields and the couplings from _u_ _[⊤]_ _u_ . Recall _u_ = [�] _j_ _[K]_ =1 [(] _[J][j]_ _[−]_ _[p][j]_ [)] _[λ][j]_ [.]
Then

1

[1]
2 _[u][⊤][u]_ [ =]

2

_K_

( _Jj_ _−_ _pj_ )( _Jk −_ _pk_ ) _λ_ _[⊤]_ _j_ _[λ][k][.]_
_j,k_ =1

Expanding ( _Jj_ _−_ _pj_ )( _Jk −_ _pk_ ) and separating the _j_ = _k_ and _j_ = _k_ parts gives

�� 21 _[−]_ _[p][j]_ - _∥λj∥_ [2] _−_ - _pk λ_ _[⊤]_ _j_ _[λ][k]_ - _Jj_ + _C_ ( _J_ ) _._

_k_ = _j_

1

[1]
2 _[u][⊤][u]_ [ =]

2

( _λ_ _[⊤]_ _j_ _[λ][k]_ [)] _[J][j][J][k]_ [+]
_j_ = _k_

_K_

_j_ =1

Absorbing the constant into _Cy_ ( _ε_ ) yields (13)–(14). Finally, the bound (15) follows from _B_ 3 _≤_
(max _j ∥λ_ [˜] _j∥_ ) _B_ 2.

**Remark** **2** (Ising on _±_ 1 spins and the choice of label set for _Y_ ) **.** _The_ _result_ _is_ _naturally_ _stated_
_with_ _Y_ _∈{_ 0 _,_ 1 _}_ _here_ _since_ _Y_ _∼_ Bernoulli( _π_ ) _and_ _ηj_ ( _y_ ) = _ajy_ + _bj._ _If_ _one_ _prefers_ _Y_ _∈{±_ 1 _},_ _set_
_Y_ ˜ := 2 _Y_ _−_ 1 _and_ _rewrite_ _ηj_ ( _Y_ ) = _bj_ + _ajY_ = ( _bj_ + [1] _[a][j]_ [) + (] [1] _[a][j]_ [) ˜] _[Y][ .]_

_Y_ ˜ := 2 _Y_ _−_ 1 _and_ _rewrite_ _ηj_ ( _Y_ ) = _bj_ + _ajY_ = ( _bj_ + [1] 2 _[a][j]_ [) + (] [1] 2 _[a][j]_ [) ˜] _[Y][ .]_

_For_ _the_ _observed_ _binary_ _variables,_ _define_ _spins_ _Xj_ := 2 _Jj_ _−_ 1 _∈{±_ 1 _}._ _Then_ _Jj_ = ( _Xj_ + 1) _/_ 2 _,_
_and_ _any_ _quadratic_ _MRF_

[1]

2 _[a][j]_ [) + (] [1] 2

_ajJj_ +

_j_ _j\<k_

```
log P( _J_ _| Y_ = _y_ ) = _C_ +
```

_bjkJjJk_

_j\<k_

_becomes_ _an_ _Ising_ _model_

_h_ ˜ _jXj_ +
_j_ _j\<k_

```
log P( _X_ _| Y_ = _y_ ) = _C_ [˜] +
```

- _W_ ˜ _jkXjXk,_

_j\<k_

_with_ _W_ [˜] _jk_ = _bjk/_ 4 _and_ _h_ [˜] _j_ = _aj/_ 2 + [1] 4 - _k_ = _j_ _[b][jk][.]_ _[Thus,]_ _[in]_ [(13)] _[,]_ _[the]_ _[{±]_ [1] _[}]_ _[couplings]_ _[are]_ _[W]_ [˜] _[jk]_ [=]

( _λ_ _[⊤]_ _j_ _[λ][k]_ [)] _[/]_ [4] _[up]_ _[to]_ _[O]_ [(] _[ε]_ [3][)] _[,]_ _[and]_ _[the]_ _[low-rank]_ _[structure]_ _[is]_ _[preserved]_ _[(scaling]_ _[does]_ _[not]_ _[change]_ _[rank).]_

**Remark** **3.** _The_ _reduction_ _from_ _a_ _latent-factor_ _model_ _to_ _an_ _(approximately)_ _pairwise_ _Ising_ _model_
_is_ _inherently_ _a_ local _approximation_ _in_ _a_ _“coupling_ _strength”_ _parameter._ _When_ _ε_ _is_ _not_ _small,_ _the_
_neglected terms in L_ [(] _ε_ _[y]_ [)][(] _[J]_ [)] _[ need not be well-approximated by a pairwise Ising energy.]_ _[The next terms]_
_in_ _the_ _Taylor/cumulant_ _expansion_ _generate_ higher-order interactions _:_ _in_ _general,_

_h_ [(] _j_ _[y]_ [)] _[J][j]_ [+]
_j_ _j\<k_

_Ujkℓ_ [(] _[y]_ [)] _[J][j][J][k][J][ℓ]_ [+] _[ · · ·]_ _[,]_ (20)
_j\<k\<ℓ_

```
log P _ε_ ( _J_ _| Y_ = _y_ ) = _C_ ( _ε_ ) +
```

- _Wjk_ [(] _[y]_ [)] _[J][j][J][k]_ [ +]
  _j\<k_ _j\<k\<ℓ_

_where_ _the_ _leading_ _triple-interaction_ _coefficients_ _scale_ _like_

_Ujkℓ_ [(] _[y]_ [)] [=] _[ O]_ - _ε_ [3] _κ_ 3( _Z_ ) _u_ [(] _j_ _[y]_ [)] _[u]_ _k_ [(] _[y]_ [)] _[u]_ _ℓ_ [(] _[y]_ [)]

24

_(and_ _more_ _generally_ _the_ _order-m_ _coefficients_ _scale_ _with_ _ε_ _[m]_ _times_ _the_ _mth_ _cumulant_ _of_ _Z_ _and_
_higher_ _derivatives_ _of_ _A)._ _Therefore,_ _if_ _the_ _latent_ _factor_ _distribution_ _is_ non-Gaussian _(skewed,_ _so_
_κ_ 3( _Z_ ) = 0 _),_ _a_ third-order _Ising/log-linear_ _model_ _(i.e.,_ _adding_ _JjJkJℓ_ _terms)_ _is_ _the_ _natural_ _next_
_approximation_ _beyond_ _pairwise._ _In_ _the_ _logistic-normal_ _case_ _we_ _considered_ _(i.e.,_ _Z_ _Gaussian_ _with_
_mean_ _zero),_ _κ_ 3( _Z_ ) = 0 _so_ _the_ _leading_ _correction_ _after_ _the_ _pairwise_ _term_ _typically_ _begins_ _at_ _order_ _ε_ [4]

_(corresponding_ _to_ _four-way_ _interactions);_ _nevertheless,_ _for_ _moderate-to-large_ _ε_ _it_ _can_ _still_ _be_ _impor-_
_tant_ _to_ _move_ _beyond_ _pairwise_ _models,_ _either_ _by_ _fitting_ _a_ _higher-order_ _log-linear_ _model_ _as_ _in_ (20) _or_
_by_ _performing_ _inference_ _directly_ _in_ _the_ _latent-factor_ _model_ _without_ _truncating_ _the_ _expansion._

**C.3.1** **Suboptimality** **of** **CI-Posterior** **under** **Latent-factors**

We now show a separation result between (exchangeable) latent-factor models and conditionally
independent models. Fix parameters _a, b, λ_ _∈_ R and _σZ_ [2] _[>]_ [0,] [and] [let] _[σ]_ [(] _[t]_ [)] [=] [(1 +] _[ e][−][t]_ [)] _[−]_ [1] [denote]
the logistic function. Let _Z_ _∼N_ (0 _, σZ_ [2] [)] [be] [a] [scalar] [latent] [factor] [independent] [of] _[Y]_ [ .] [Conditional] [on]
( _Y_ = _y, Z_ = _z_ ), the _K_ judges produce i.i.d. votes

_J_ 1 _, . . ., JK_ ( _Y_ = _y, Z_ = _z_ ) iid _∼_ Bernoulli� _p_ ( _y, z_ )� _,_ _p_ ( _y, z_ ) := _σ_ - _b_ + _a_ (2 _y −_ 1) + _λ_ (2 _y −_ 1) _z_ - _._
���

(21)

Note that _λ ̸_ = 0 and _σZ_ [2] _[>]_ [ 0] [imply] [a] [nondegenerate] [factor] [that] [induces] [dependence] [among] [judges]
given _Y_ . Write _SK_ = [�] _j_ _[K]_ =1 _[J][j]_ [and] _[s][K]_ [=] _[ S][K][/K]_ [.]
We now discuss the true posterior and Bayes rule under these model. Let P _[⋆]_ ( _· | J_ ) denote the
posterior under the true model (21), and define the Bayes predictor

_gK_ _[⋆]_ [(] _[J]_ [) :=] **[ 1]** �P _[⋆]_ ( _Y_ = 1 _| J_ ) _≥_ 2 [1] - _._

**Conditional-independence (CI) Predictor.** Define the class-conditional marginal success probabilities
Pmarg( _y_ ) := E _Z_ �P( _y, Z_ )� _∈_ (0 _,_ 1) _,_ _y_ _∈{_ 0 _,_ 1 _}._

The CI approximation replaces the true joint likelihood by the product of marginal Bernoulli
likelihoods, i.e.,

```
- _K_
```

_L_ [ind] _y_ [(] _[S]_ [) :=]
_S_

Pmarg( _y_ ) _[S]_ [�] 1 _−_ Pmarg( _y_ )� _K−S._

Let P [ind] ( _· | J_ ) be the posterior induced by _L_ [ind] _y_ and prior _π_, and define

_gK_ [ind][(] _[J]_ [) :=] **[ 1]** �P [ind] ( _Y_ = 1 _| J_ ) _≥_ 2 [1] - _._

Define the Bernoulli KL divergence for _s, q_ _∈_ (0 _,_ 1) by

_[s]_ [1] _[ −]_ _[s]_

_q_ [+ (1] _[ −]_ _[s]_ [) log] 1 _−_ _q_

KL( _s∥q_ ) := _s_ log _[s]_

1 _−_ _q_ _[.]_

**Theorem** **3** (Asymptotic Bayes-CI separation under an exchangeable logistic-normal factor) **.** _As-_
_sume_ _the_ _exchangeable_ _latent-factor_ _model_ (21) _with_ _λ_ = 0 _and_ _σZ_ [2] _[>]_ [0] _[.]_ _[Let]_ _[S][K]_ [=] [�] _j_ _[K]_ =1 _[J][j]_ _[and]_
_sK_ = _SK/K._ _Write_ _qy_ := Pmarg( _y_ ) = E _Z_ \[P( _y, Z_ )\] _∈_ (0 _,_ 1) _._ _Define,_ _for_ _s ∈_ (0 _,_ 1) _,_

logit( _s_ ) := log _s_ _ℓ_ _[⋆]_ ( _s_ ) := log _π_ 2 _a_ - logit( _s_ ) _−_ _b_ - _,_
1 _−_ _s_ _[,]_ 1 _−_ _π_ [+] _λ_ [2] _σZ_ [2]

25

_and_
_ℓ_ [ind] ( _s_ ) := _s_ log _[q]_ [1]

= _−_ KL( _s∥q_ 1) + KL( _s∥q_ 0) _._
1 _−_ _q_ 0

_[q]_ [1] + (1 _−_ _s_ ) log [1] _[ −]_ _[q]_ [1]

_q_ 0 1 _−_ _q_ 0

_Let_ _s∞_ := _p_ ( _Y, Z_ ) _∈_ (0 _,_ 1) _._
_Assume_ _the_ _(mild)_ _no-tie_ _conditions_

P� _ℓ_ _[⋆]_ ( _s∞_ ) = 0� = 0 _,_ P� _ℓ_ [ind] ( _s∞_ ) = 0� = 0 _._

_Then,_ _as_ _K_ _→∞,_

a _._ s _._ a _._ s _._
_gK_ _[⋆]_ _−−→_ _g∞_ _[⋆]_ [:=] **[ 1]** _[{][ℓ][⋆]_ [(] _[s][∞]_ [)] _[ ≥]_ [0] _[}][,]_ _gK_ [ind] _−−→_ _g∞_ [ind] [:=] **[ 1]** _[{][ℓ]_ [ind][(] _[s][∞]_ [)] _[ ≥]_ [0] _[}][,]_

_and_ _the_ _excess_ _risk_ _has_ _the_ _limit_

```
              -                  lim      - _R_ ( _gK_ [ind][)] _[ −]_ _[R]_ [(] _[g]_ _K_ _[⋆]_ [)]      - = E _|_ 2 _η∞_ _−_ 1 _| ·_ **1** _{g∞_ [ind] [=] _[ g]_ _∞_ _[⋆]_ _[}]_ _,_ _η∞_ := _σ_      - _ℓ_ _[⋆]_ ( _s∞_ )� _._
```

_K→∞_

_In_ _particular,_ _if_ P( _g∞_ [ind] [=] _[ g]_ _∞_ _[⋆]_ [)] _[ >]_ [ 0] _[,]_ _[then]_ _[the]_ _[limit]_ _[is]_ _[strictly]_ _[positive.]_

_Proof._ We start with a reduction to the sufficient statistic _SK_ . Fix _y_ _∈{_ 0 _,_ 1 _}_ and let _j_ =
( _j_ 1 _, . . ., jK_ ) _∈{_ 0 _,_ 1 _}_ _[K]_ with [�] _k_ _[K]_ =1 _[j][k]_ [=] _[ S]_ [.] [Under] [(21),] [we] [have] [that]

_p_ ( _y, z_ ) _[S]_ (1 _−p_ ( _y, z_ )) _[K][−][S]_ _ϕσZ_ ( _z_ ) _dz,_

R

```
    P( _J_ = _j_ _| Y_ = _y_ ) =
```

R

_K_

_p_ ( _y, z_ ) _[j][k]_ (1 _−p_ ( _y, z_ )) [1] _[−][j][k]_ _ϕσZ_ ( _z_ ) _dz_ =

_k_ =1

which depends on _j_ only through _S_ . Hence _SK_ is sufficient for _Y_ under the true model, and likewise
_SK_ is sufficient under the CI model by construction. Therefore both posteriors and both decision
rules can be written as functions of _SK_ (equivalently _sK_ ).
We next derive almost sure limits of the vote fraction. First condition on ( _Y_ = _y, Z_ = _z_ ).
Then _J_ 1 _, . . ., JK_ are i.i.d. Bernoulli( _p_ ( _y, z_ )), so by the strong law, _sK_ _→_ _p_ ( _y, z_ ) almost surely.
Unconditioning yields _sK_ _→_ _p_ ( _Y, Z_ ) =: _s∞_ almost surely.
We now derive sharp asymptotics of the true marginal likelihood _L_ _[⋆]_ _y_ [(] _[S]_ [).] [Recall]

- _K_
  _L_ _[⋆]_ _y_ [(] _[S]_ [) =]
  _S_

��

_p_ ( _y, z_ ) _[S]_ (1 _−_ _p_ ( _y, z_ )) _[K][−][S]_ _ϕσZ_ ( _z_ ) _dz._

R

Fix _s_ _∈_ (0 _,_ 1) and take _S_ = _⌊Ks⌋_ (so _S/K_ _→_ _s_ ). By Stirling’s formula, uniformly for _s_ in any
compact \[ _ε,_ 1 _−_ _ε_ \] _⊂_ (0 _,_ 1),

- _K_ - = 1 + _o_ (1) exp - _KH_ ( _s_ )� _,_ _H_ ( _s_ ) := _−s_ log _s −_ (1 _−_ _s_ ) log(1 _−_ _s_ ) _._
  _S_ ~~�~~ 2 _πKs_ (1 _−_ _s_ )

Furthermore, we have that

```
          -               _p_ ( _y, z_ ) _[S]_ (1 _−_ _p_ ( _y, z_ )) _[K][−][S]_ = exp _K_    - _s_ log _p_ ( _y, z_ ) + (1 _−_ _s_ ) log(1 _−_ _p_ ( _y, z_ ))� + _o_ ( _K_ ) _._
```

Now, using the identity

_s_ log _q_ + (1 _−_ _s_ ) log(1 _−_ _q_ ) = _−_ KL( _s∥q_ ) _−_ _H_ ( _s_ ) ( _q_ _∈_ (0 _,_ 1))

gives

1 + _o_ (1)
_L_ _[⋆]_ _y_ [(] _[S]_ [) =] ~~�~~ 2 _πKs_ (1 _−_ _s_ )

exp� _−_ _K ψy_ ( _z_ ; _s_ )� _ϕσZ_ ( _z_ ) _dz,_ _ψy_ ( _z_ ; _s_ ) := KL� _s∥p_ ( _y, z_ )� _,_

R

26

uniformly for _s_ in compact subsets of (0 _,_ 1).
Because _λ ̸_ = 0, the map _z_ _�→_ _p_ ( _y, z_ ) is strictly monotone and continuous with range (0 _,_ 1). Hence
for each _s_ _∈_ (0 _,_ 1) there is a unique _zy_ ( _s_ ) _∈_ R such that _p_ ( _y, zy_ ( _s_ )) = _s_ . Since KL( _s∥q_ ) _≥_ 0 with
equality iff _q_ = _s_, we have _ψy_ ( _z_ ; _s_ ) _≥_ 0 with a unique minimizer at _z_ = _zy_ ( _s_ ) and _ψy_ ( _zy_ ( _s_ ); _s_ ) = 0.
Moreover, _ψy_ ( _·_ ; _s_ ) has a nondegenerate quadratic minimum at _zy_ ( _s_ ). Indeed, write _q_ ( _z_ ) :=
_p_ ( _y, z_ ) and note that for fixed _s_,

_d_ [2] 1

_dq_ [2] [KL][(] _[s][∥][q]_ [)] ��� _q_ = _s_ [=] _s_ (1 _−_ _s_ ) _[.]_

By the chain rule and _q_ _[′]_ ( _z_ ) = _λ_ (2 _y −_ 1) _q_ ( _z_ )(1 _−_ _q_ ( _z_ )), we get at _z_ = _zy_ ( _s_ ) (where _q_ ( _z_ ) = _s_ )

_∂_ [2] 1 - _q_ _[′]_ ( _zy_ ( _s_ ))�2 = 1 - _λ_ (2 _y −_ 1) _s_ (1 _−_ _s_ )�2 = _λ_ 2 _s_ (1 _−_ _s_ ) _>_ 0 _._

_∂z_ [2] _[ψ][y]_ [(] _[z]_ [;] _[ s]_ [)] ��� _z_ = _zy_ ( _s_ ) [=] _s_ (1 _−_ _s_ ) _s_ (1 _−_ _s_ )

Therefore Laplace’s approximation method (for an interior, nondegenerate minimum) yields, uniformly for _s_ in compact subsets of (0 _,_ 1),

~~�~~

�R exp� _−_ _K ψy_ ( _z_ ; _s_ )� _ϕσZ_ ( _z_ ) _dz_ = _ϕσZ_ - _zy_ ( _s_ )� _Kλ_ [2] _s_ 2(1 _π −_ _s_ ) [(1 +] _[ o]_ [(1))] _[.]_

Combining the last two displays gives the desired sharp 1 _/K_ -scale asymptotic:

_[ o]_ [(1)]

_fy_ ( _s_ ) _,_ _fy_ ( _s_ ) := _[ϕ][σ][Z]_ [(] _[z][y]_ [(] _[s]_ [))]
_K_ _|λ| s_ (1 _−_ _s_

_L_ _[⋆]_ _y_ [(] _[⌊][Ks][⌋]_ [) =] [1 +] _[ o]_ [(1)]

_[Z]_ (22)

_|λ| s_ (1 _−_ _s_ ) _[.]_

In the above _fy_ is indeed exactly the density of the transformed random variable _p_ ( _y, Z_ ) by change
of variables.
We now proceed with the limit of the true posterior and Bayes decision. By the aforementioned
sufficiency argument, we have that

_πL_ _[⋆]_ 1 [(] _[S][K]_ [)]
_ηK_ := P _[⋆]_ ( _Y_ = 1 _| J_ ) = P _[⋆]_ ( _Y_ = 1 _| SK_ ) =
_πL_ _[⋆]_ 1 [(] _[S][K]_ [) + (1] _[ −]_ _[π]_ [)] _[L][⋆]_ 0 [(] _[S][K]_ [)] _[.]_

Let _sK_ = _SK/K_ _→_ _s∞_ almost surely by Step 1. Applying (22) to the (random) sequence _sK_ (using
local uniformity on a neighborhood of the a.s. limit point _s∞_ _∈_ (0 _,_ 1)), we obtain almost surely

_L_ _[⋆]_ 1 [(] _[S][K]_ [)]
_L_ _[⋆]_ 0 [(] _[S][K]_ [)] _[→]_ _[f]_ _f_ [1] 0 [(] ( _[s]_ _s_ _[∞]_ _∞_ [)] ) _[.]_

Now compute _f_ 1 _/f_ 0 explicitly. Writing _θ_ := logit( _s_ ), the unique solutions to _p_ ( _y, z_ ) = _s_ are

_z_ 1( _s_ ) = _[θ][ −]_ [(] _[b]_ [ +] _[ a]_ [)]

_[b]_ [ +] _[ a]_ [)]

_,_ _z_ 0( _s_ ) = [(] _[b][ −]_ _[a]_ [)] _[ −]_ _[θ]_
_λ_ _λ_

_._
_λ_

The Jacobian factors in (22) cancel because _|λ|_ is the same for _y_ = 0 _,_ 1, so

```
 - _z_ 0( _s_ )2 _−_ _z_ 1( _s_ )2
```

_[ϕ][σ][Z]_ [(] _[z]_ [1][(] _[s]_ [))]

_ϕσZ_ ( _z_ 0( _s_ )) [= exp] 2 _σZ_ [2]

_f_ 1( _s_ )

_[ϕ][σ][Z]_ [(] _[z]_ [1][(] _[s]_ [))]
_f_ 0( _s_ ) [=] _ϕσZ_ ( _z_ 0( _s_ ))

2 _σZ_ [2]

_._

A direct algebraic simplification gives

_z_ 0( _s_ ) [2] _−_ _z_ 1( _s_ ) [2] = [(] _[b][ −]_ _[a][ −]_ _[θ]_ [)][2] _[ −]_ [(] _[θ][ −]_ _[b][ −]_ _[a]_ [)][2]

_._
_λ_ [2]

[(] _[θ][ −]_ _[b][ −]_ _[a]_ [)][2]

= [4] _[a]_ [(] _[θ][ −]_ _[b]_ [)]
_λ_ [2] _λ_ [2]

27

Hence

_πf_ 1( _s_ ) _π_ 2 _a_
log
(1 _−_ _π_ ) _f_ 0( _s_ ) [= log] 1 _−_ _π_ [+] _λ_ [2] _σZ_ [2]

- logit( _s_ ) _−_ _b_ - = _ℓ_ _[⋆]_ ( _s_ ) _,_

and therefore almost surely
_ηK_ _→_ _η∞_ := _σ_ - _ℓ_ _[⋆]_ ( _s∞_ )� _._

Since _gK_ _[⋆]_ [=] **[ 1]** _[{][η][K]_ _[≥]_ [1] _[/]_ [2] _[}]_ [and] [P(] _[ℓ][⋆]_ [(] _[s][∞]_ [) = 0) = 0] [by] [assumption,] [the] [sign] [stabilizes] [and]

_gK_ _[⋆]_ _[→]_ **[1]** _[{][ℓ][⋆]_ [(] _[s][∞]_ [)] _[ ≥]_ [0] _[}]_ [ =] _[ g]_ _∞_ _[⋆]_ a.s.

Next, we derive the limit of the CI decision rule. Under CI, we have that

```
         - _K_
```

_L_ [ind] _y_ [(] _[S]_ [) =]
_S_

Thus the CI log-posterior odds equal

_qy_ _[S]_ [(1] _[ −]_ _[q][y]_ [)] _[K][−][S][.]_

[= 1] _[ |][ S][K]_ [)]
log [P][ind][(] _[Y]_

_[q]_ [1] + ( _K −_ _SK_ ) log [1] _[ −]_ _[q]_ [1]

_q_ 0 1 _−_ _q_ 0

[P] [(] _[Y]_ [= 1] _[ |][ S][K]_ [)] _π_ _[q]_ [1]

P [ind] ( _Y_ = 0 _| SK_ ) [= log] 1 _−_ _π_ [+] _[ S][K]_ [ log] _q_ 0

[1] _[ −]_ _[q]_ [1] = log _π_

1 _−_ _q_ 0 1 _−_ _π_ [+] _[ K ℓ]_ [ind][(] _[s][K]_ [)] _[.]_

Since _sK_ _→_ _s∞_ almost surely and P( _ℓ_ [ind] ( _s∞_ ) = 0) = 0, the term _K ℓ_ [ind] ( _sK_ ) diverges to _±∞_ with
the sign of _ℓ_ [ind] ( _s∞_ ), hence

_gK_ [ind] [=] **[ 1]** _[{]_ [P][ind][(] _[Y]_ [= 1] _[ |][ S][K]_ [)] _[ ≥]_ [1] _[/]_ [2] _[} →]_ **[1]** _[{][ℓ]_ [ind][(] _[s][∞]_ [)] _[ ≥]_ [0] _[}]_ [ =] _[ g]_ _∞_ [ind] a.s.

We are now ready to calculate the excess risks. For any (measurable) classifier _g_ ( _J_ ) _∈{_ 0 _,_ 1 _}_,

P( _g_ ( _J_ ) _̸_ = _Y_ _| J_ ) = _ηK_ **1** _{g_ ( _J_ ) = 0 _}_ + (1 _−_ _ηK_ ) **1** _{g_ ( _J_ ) = 1 _}._

The Bayes rule _gK_ _[⋆]_ [=] **[ 1]** _[{][η][K]_ _[≥]_ [1] _[/]_ [2] _[}]_ [minimizes] [this] [conditional] [risk,] [and] [a] [direct] [case] [check] [gives]

P( _g_ ( _J_ ) _̸_ = _Y_ _| J_ ) _−_ P( _gK_ _[⋆]_ [(] _[J]_ [)] _[ ̸]_ [=] _[ Y]_ _[|][ J]_ [) =] _[ |]_ [2] _[η][K]_ _[−]_ [1] _[| ·]_ **[ 1]** _[{][g]_ [(] _[J]_ [)] _[ ̸]_ [=] _[ g]_ _K_ _[⋆]_ [(] _[J]_ [)] _[}][.]_

Taking expectations and substituting _g_ = _gK_ [ind] yields the exact finite- _K_ identity

```
                  -                      _R_ ( _gK_ [ind][)] _[ −]_ _[R]_ [(] _[g]_ _K_ _[⋆]_ [) =][ E] _|_ 2 _ηK_ _−_ 1 _| ·_ **1** _{gK_ [ind] [=] _[ g]_ _K_ _[⋆]_ _[}]_ _._
```

Note that we also have _ηK_ _→_ _η∞_ and _gK_ [ind] _→_ _g∞_ [ind] and _gK_ _[⋆]_ _[→]_ _[g]_ _∞_ _[⋆]_ [almost] [surely.] [Since] [the]
integrand is bounded by 1, dominated convergence gives

```
                   -                        lim           - _R_ ( _gK_ [ind][)] _[ −]_ _[R]_ [(] _[g]_ _K_ _[⋆]_ [)]           - = E _|_ 2 _η∞_ _−_ 1 _| ·_ **1** _{g∞_ [ind] [=] _[ g]_ _∞_ _[⋆]_ _[}]_ _._
```

_K→∞_

Finally, on the event _{g∞_ [ind] [=] _[g]_ _∞_ _[⋆]_ _[}]_ [we] [must] [have] _[η][∞]_ [=] [1] _[/]_ [2] [(since] _[g]_ _∞_ _[⋆]_ [is] [the] [threshold] [at] [1] _[/]_ [2),] [so]
_|_ 2 _η∞_ _−_ 1 _| >_ 0 there; thus if P( _g∞_ [ind] [=] _[ g]_ _∞_ _[⋆]_ [)] _[ >]_ [ 0] [the] [expectation] [is] [strictly] [positive.]

Theorem 3 formalizes a simple but important phenomenon: if the judges share a _common_ _latent_
_factor_ that affects their votes, then their votes are _dependent_ given the label, and a CI-predictor
can remain strictly suboptimal even as the number of judges _K_ grows.
In the logistic-normal factor model, conditional on the label _Y_ and a latent scalar _Z_, the judges
vote independently:
_J_ 1 _, . . ., JK_ �� ( _Y, Z_ ) i.i.d. Bernoulli�P( _Y, Z_ )� _._

28

The key point is that _Z_ is _shared_ _across_ _all_ _judges_ for a given item, so after marginalizing out _Z_
the votes are no longer independent given _Y_ . Equivalently, _Z_ induces a label-dependent correlation/failure mode (e.g. shared bias, shared noise, or common difficulty of the item).
Now, we discuss the case what happens when _K_ _→∞_ . As the number of judges grows, the
empirical vote fraction

_sK_ = [1]

_K_

_K_

_Jj_

_j_ =1

concentrates almost surely around the random limit

_s∞_ = P( _Y, Z_ ) _._

Thus, with many judges, the data effectively reveals the latent factor through the realized value of
_s∞_ (because different _Z_ values shift the success probability).
The Bayes posterior P( _Y_ = 1 _|_ _J_ ) integrates over _Z_ using the correct mixture likelihood. In
this specific logistic-normal setup, the large- _K_ limit of the Bayes posterior depends on _s∞_ through
an explicit one-dimensional score

_π_ 2 _a_
_ℓ_ _[⋆]_ ( _s∞_ ) = log
1 _−_ _π_ [+] _λ_ [2] _σZ_ [2]

so the Bayes predictor converges to the limiting rule

- logit( _s∞_ ) _−_ _b_ - _,_

_g∞_ _[⋆]_ [=] **[ 1]** _[{][ℓ][⋆]_ [(] _[s][∞]_ [)] _[ ≥]_ [0] _[}][.]_

Intuitively, Bayes predictor recognizes that extreme values of the vote fraction _s∞_ may be better
explained by certain _Z_ realizations under one class than the other.
Under CI the true joint likelihood is replaced by a product of class-conditional marginals. This
yields a different limiting score,

_[q]_ [1] + (1 _−_ _s∞_ ) log [1] _[ −]_ _[q]_ [1]

_q_ 0 1 _−_ _q_ 0

_ℓ_ [ind] ( _s∞_ ) = _s∞_ log _[q]_ [1]

_,_ _qy_ = E _Z_ \[ _p_ ( _y, Z_ )\] _,_
1 _−_ _q_ 0

and hence a potentially different limiting decision

_g∞_ [ind] [=] **[ 1]** _[{][ℓ]_ [ind][(] _[s][∞]_ [)] _[ ≥]_ [0] _[}][.]_

Because CI discards the correlation structure induced by _Z_, it generally assigns different relative
likelihoods to the same observed vote fraction _s∞_ than the true Bayes model does.
In summary, the proposition shows that both rules converge (almost surely) to deterministic
limit classifiers that depend only on _s∞_ = _p_ ( _Y, Z_ ). Moreover, it gives an exact expression for the
asymptotic excess risk:

```
                   -                        lim           - _R_ ( _gK_ [ind][)] _[ −]_ _[R]_ [(] _[g]_ _K_ _[⋆]_ [)]           - = E _|_ 2 _η∞_ _−_ 1 _| ·_ **1** _{g∞_ [ind] [=] _[ g]_ _∞_ _[⋆]_ _[}]_ _,_
```

_K→∞_

where _η∞_ is the limiting Bayes posterior. This quantity is strictly positive whenever the limiting CI
and Bayes decisions disagree on a set of latent-factor realizations of positive probability. In other
words, adding more judges does not necessarily save CI; as _K_ grows, the ensemble increasingly
reveals the shared latent factor, and Bayes exploits it, but CI cannot, so the performance gap can
converge to a nonzero constant.

29

### **D Posterior Inference with Unknown Labels via (Generalized) EM**

Recall that, all models in this paper share the same high-level structure: each item _i_ _∈{_ 1 _, . . ., n}_
has an unobserved label _Yi_ _∈{_ 0 _,_ 1 _}_ and an observed vote vector _Ji_ = ( _Ji_ 1 _, . . ., JiK_ ) _∈{_ 0 _,_ 1 _}_ _[K]_ . The
joint model factorizes across items as

PΘ( _{Yi, Ji}_ _[n]_ _i_ =1 [) =]

_n_

PΘ( _Yi_ ) PΘ( _Ji_ _| Yi_ ) _,_ PΘ( _Yi_ = 1) = _π,_ (23)

_i_ =1

where Θ denotes model parameters (e.g., CI accuracies, Ising fields/couplings, latent-factor loadings, etc.). The inferential goal is to compute the posterior label probabilities _γi_ := PΘ( _Yi_ = 1 _|_
_Ji_ ) _,_ _i_ = 1 _, . . ., n,_ and to produce point predictions _Y_ [ˆ] _i_ = **1** _{γi_ _≥_ 1 _/_ 2 _}_ .
We use the Expectation-Maximization framework [12] for the above purpose. The observed-data
log-likelihood is

_n_

- -

_ℓ_ (Θ) := log _π_ PΘ( _Ji_ _| Yi_ = 1) + (1 _−_ _π_ ) PΘ( _Ji_ _| Yi_ = 0) _._ (24)

_i_ =1

EM maximizes _ℓ_ (Θ) by iteratively optimizing a lower bound based on the complete-data loglikelihood. Given current parameters Θ [(] _[t]_ [)], define

_γi_ [(] _[t]_ [)] := PΘ( _t_ )( _Yi_ = 1 _| Ji_ ) _,_ 1 _−_ _γi_ [(] _[t]_ [)] = PΘ( _t_ )( _Yi_ = 0 _| Ji_ ) _._

The expected complete-data objective (the _Q_ -function) is then given by

_Q_ (Θ _|_ Θ [(] _[t]_ [)] ) :=

_n_

- E _Yi|Ji_ ;Θ( _t_ )� log PΘ( _Yi, Ji_ )�

_i_ =1

\=

-

_n_

_i_ =1

_n_

_i_ =1

- _γi_ [(] _[t]_ [)] log _π_ + (1 _−_ _γi_ [(] _[t]_ [)][) log(1] _[ −]_ _[π]_ [)]

- _γi_ [(] _[t]_ [)] log PΘ( _Ji_ _| Yi_ = 1) + (1 _−_ _γi_ [(] _[t]_ [)][) log P][Θ][(] _[J][i]_ _[|][ Y][i]_ [= 0)] _._

When we include regularization or Bayesian priors, we maximize _Q_ (Θ _|_ Θ [(] _[t]_ [)] ) + log P(Θ) instead
(MAP-EM). The overall procedure is provided in Algorithm 1. We emphasize that the procedure
is purely unsupervised.

**D.1** **Specializations** **of** **Algorithm** **1**

In the conditionally independent (CI) family, including Dawid-Skene and its asymmetric sensitivity/specificity variants, the class-conditional likelihood factorizes across judges: PΘ( _Ji_ _|_ _Yi_ = _y_ ) =

- _Kj_ =1 [P][Θ][(] _[J][ij]_ _[|][ Y][i]_ [=] _[ y]_ [)] _[.]_ [ As a result, the E-step is exact and inexpensive:] [the score difference] _[ℓ]_ [�] _[i]_ [1] _[ −]_ _[ℓ]_ [�] _[i]_ [0]
  is just a sum of per-judge log-likelihood ratios, yielding closed-form responsibilities _γi_ via a logistic
  transform. The M-step is also simple: maximizing (26) reduces to fitting per-judge Bernoulli parameters from soft counts, i.e., weighted averages of votes under _γi_ (and 1 _−_ _γi_ ), together with the
  closed-form update for the class prior. This recovers the classical David-Skene EM algorithm [12]
  as a special case of Algorithm 1.
  For latent-factor models, the conditional likelihood typically has the form PΘ( _Ji_ _|_ _Yi_ = _y_ ) =

- PΘ( _Ji_ _| Yi_ = _y, Zi_ = _z_ ) PΘ( _z_ ) _dz,_ where _Zi_ is a per-item latent variable (e.g., item difficulty, topic,

30

**Algorithm** **1** Generalized EM for unsupervised binary label aggregation (CI, latent factors, Ising)

1: **Input:** votes _Ji_ _∈{_ 0 _,_ 1 _}_ _[K]_ for _i_ = 1 _, . . ., n_ ; model family _P_ Θ( _J_ _|_ _Y_ ); initialization Θ [(0)] ;
tolerances.

2: **for** _t_ = 0 _,_ 1 _,_ 2 _, . . ._ until convergence **do**

3: **E-step** **(posterior** **labels):** For each item _i_, compute class scores

_ℓ_ - [(] _iy_ _[t]_ [)] _[≈]_ [log] _[ P]_ Θ [(] _[t]_ [)][(] _[J][i]_ _[|][ Y][i]_ [=] _[ y]_ [)] _[,]_ _y_ _∈{_ 0 _,_ 1 _},_

using an exact evaluator (when tractable) or an approximation (e.g. mean-field, loopy BP,
Monte Carlo, or a variational bound). Set

```
               -                    _γi_ [(] _[t]_ [)] _←_ _P_ Θ( _t_ )( _Yi_ = 1 _| Ji_ ) = _σ_ logit( _π_ [(] _[t]_ [)] ) + _ℓ_ [�][(] _i_ 1 _[t]_ [)] _[−]_ _[ℓ]_ [�] _i_ [(] 0 _[t]_ [)] _,_ (25)
```

where _σ_ ( _u_ ) = (1 + _e_ _[−][u]_ ) _[−]_ [1] .

4: **M-step** **(parameter** **update):** Update the class prior (MLE form)

_π_ [(] _[t]_ [+1)] _←_ [1]

_n_

_n_

_γi_ [(] _[t]_ [)] (or MAP update if a Beta prior is used).
_i_ =1

Update remaining parameters by (approximately) maximizing the weighted objective

- _γi_ [(] _[t]_ [)] log _P_ Θ( _Ji_ _| Yi_ = 1) + (1 _−_ _γi_ [(] _[t]_ [)][) log] _[ P]_ [Θ][(] _[J][i]_ _[|][ Y][i]_ [= 0)] + log _p_ (Θ) _,_

(26)

Θ [(] _[t]_ [+1)] _∈_ arg max
Θ

_n_

_i_ =1

using a model-appropriate solver (closed-form updates, gradient methods, pseudo-likelihood,
etc.).

5: **end** **for**

6: **Output:** parameters Θ [�] and posteriors _γ_ - _i_ ; predicted labels _Y_ [�] _i_ = **1** _{γ_ - _i_ _≥_ 1 _/_ 2 _}_ .

or shared failure mode). The E-step therefore requires marginalizing over _Zi_, which is generally
not available in closed form in flexible models. In practice one can compute approximate class
scores _ℓ_ [�] _iy_ using a tractable approximation to the integral, such as a variational bound, Laplace
approximation, or Monte Carlo estimate, and then form _γi_ as in (25). The M-step becomes a
(regularized) maximum-likelihood or MAP problem for the latent-factor parameters (loadings, biases, prior variance, etc.) with soft labels; we solve it with gradient-based optimization, optionally
interleaving updates for per-item latent posterior parameters (as in variational EM) when a fully
Bayesian treatment of _Zi_ is used.
For Ising models, the main difficulty is that the exact likelihood PΘ( _Ji_ _|_ _Yi_ = _y_ ) involves the
partition function _Z_ [(] _[y]_ [)] (Θ), making both the E-step scores and the M-step objective intractable at
scale. We therefore use the _generalized_ EM strategy based on tractable surrogates. A standard
choice (which we use in our experiments) is the (regularized) pseudo-likelihood [21], which replaces
the log-likelihood by a sum of conditional node log-likelihoods [�] _j_ [log P][Θ][(] _[J][ij]_ _[|]_ _[J][i,][−][j][, Y][i]_ [=] _[y]_ [)] [and]
avoids _Z_ [(] _[y]_ [)] entirely. In the M-step, maximizing (26) under pseudo-likelihood reduces to a set of
weighted logistic regressions (one per node) with weights given by the current responsibilities _γi_
for class _y_ = 1 and (1 _−_ _γi_ ) for class _y_ = 0. In the E-step, we can compute _ℓ_ [�] _iy_ either using the

31

same pseudo-likelihood score (yielding a fully consistent surrogate EM). Other possibilities include
using a approximate inference methods including mean-field methods [7], belief propagation [29],
or Markov chain Monte Carlo [32] to approximate the true class-conditional evidence.
Finally, we remark that for our experiments in Sections 4.1 and F, when using specific instantiations of Algorithm 1, we manually tune the hyperparameters (if any) for best performance. More
principled ways to set them include general purpose procedures like cross-validation.

**D.2** **Illustration** **of** **Theorem** **2** **via** **Algorithm** **1**

For the sake of the reader’s convenience, we connect the magnetization-threshold rule in Theorem 2
to posterior-threshold prediction as in Algorithm 1. Define for each item _i_ the (spin) magnetization

1
_Mi_ := _MK_ ( _Ji_ ) =
_K_

_K_

_Xij,_ _Xij_ := 2 _Jij_ _−_ 1 _∈{±_ 1 _}._

_j_ =1

Because the Curie-Weiss model is exchangeable, the Bayes posterior depends on the votes _Ji_
only through _Mi_ (equivalently through the vote fraction). In particular, if we form a (possibly
approximate/plug-in) posterior based on the statistic _|Mi|_,

_π_ _p_ 1( _|Mi|_ )
_γ_ - _i_ := PΘ� ( _Yi_ = 1 _| |Mi|_ ) = _π_ _p_ 1( _|Mi|_ ) + (1 � _−_ _π_ ) _p_ 0( _|Mi|_ ) _[,]_
\-

where _py_ ( _·_ ) denotes the (estimated) class-conditional pmf/density of _|MK|_ under _Y_ = _y_, then the

usual posterior-threshold prediction is

_π_
_Y_ - _i_ = **1** _{γ_ - _i_ _≥_ 1 _/_ 2 _}_ _⇐⇒_ log 1 _−_ _π_ [+ log] _[p]_ _p_ [�][1] 0 [(] ( _[|]_ _|_ _[M]_ _M_ _[i]_ _i_ _[|]_ _|_ [)] ) _[≥]_ [0] _[.]_

In the Curie-Weiss regimes used for the separation result in Theorem 2, the log-likelihood ratio
_m_ that _�→_ log _[p]_ _p_ [�] - [1] 0 [(] ( _[m]_ _m_ [)] ) [is (asymptotically) increasing in] _[ m][ ∈]_ \[[0] _[,]_ [ 1], so there exists a threshold\] _[ t][ ∈]_ [(0] _[,]_ [ 1) such]

**1** _{γi_ _≥_ 1 _/_ 2 _}_ = **1** _{|Mi| ≥_ _t}._

Thus the magnetization classifier _g_ ˜ _K_ ( _J_ ) = **1** _{|MK_ ( _J_ ) _| ≥_ _t}_ is exactly a posterior-threshold rule of
the form _Y_ [�] _i_ = **1** _{γ_ - _i_ _≥_ 1 _/_ 2 _}_ when _γ_ - _i_ is computed from (or approximated by) evidence in _|MK|_ .

### **E Proofs from Section 3**

**E.1** **Proof** **of** **Theorem** **1**

**Theorem** **1** (Nonvanishing Bayes vs. CI Separation for Class-conditional Ising Models) **.** _Fix_ _a_
_prior_ P( _Y_ = 1) = _π_ _∈_ (0 _,_ 1) _._ _For_ _each_ _K_ _≥_ 1 _,_ _let_ _J_ = ( _J_ 1 _, . . ., JK_ ) _∈{_ 0 _,_ 1 _}_ _[K]_ _denote_ _the_ _K_
_judges’_ _votes_ _for_ _a_ _single_ _item_ _and_ _define_ _the_ _recoded_ _spins_ _Xj_ := 2 _Jj_ _−_ 1 _∈{−_ 1 _,_ +1 _}_ _and_ _let_

_MK_ := _K_ 1 - _Kj_ =1 _[X][j]_ _[∈]_ - _−_ 1 _, −_ 1 + _K_ [2] _[, . . .,]_ [ 1] - _._ _Assume_ _the_ _following_ class-conditional Curie-Weiss

Ising _model:_ _there_ _exist_ _constants_ 0 _< β_ 0 _\<_ 1 _< β_ 1 _such_ _that,_ _conditional_ _on_ _Y_ = _y_ _∈{_ 0 _,_ 1 _},_

1 - _βy_
P( _X_ = _x | Y_ = _y_ ) =
_ZK_ ( _βy_ ) [exp] 2 _K_

32

- - _[K]_ _xj_ �2� _,_ (6)

_j_ =1

_for_ _x_ _∈{−_ 1 _,_ +1 _}_ _[K]_ _._ _Equivalently_ _(writing_ _xj_ = 2 _jj_ _−_ 1 _),_ _this_ _is_ _a_ _special_ _case_ _of_ _the_ _{_ 0 _,_ 1 _}-Ising_

```
      _form_ (1) _with_ _h_ [(] _j_ _[y]_ [)] = _−_ 2 _βy_ 1 _−_ [1]
```

_K_ [1] - _and_ _Wjk_ [(] _[y]_ [)] [=] [4] _K_ _[β][y]_

_[y]_ ( _j_ = _k_ ) _,_ _up_ _to_ _an_ _additive_ _constant_ _absorbed_

_K_

_into_ _Z_ [(] _[y]_ [)] _._
_Let_ _gK_ _[⋆]_ _[be]_ _[the]_ _[Bayes-optimal]_ _[predictor]_ _[under]_ _[the]_ _[true]_ _[model]_ [(6)] _[.]_ _[Let]_ _[g]_ _K_ [ind] _be_ _the_ _population_
_CI-predictor_ _that_ _replaces_ _the_ _true_ _joint_ _by_ _the_ _product_ _of_ _true_ _one-dimensional_ _marginals,_ _i.e.,_
P [ind] ( _J_ = _j_ _| Y_ = _y_ ) := [�] _r_ _[K]_ =1 _[q]_ _y_ _[j][r]_ [(1] _[ −]_ _[q]_ _y_ [)][1] _[−][j][r]_ _[with]_ _[q]_ _y_ [:= P(] _[J]_ _r_ [= 1] _[ |][ Y]_ [=] _[ y]_ [)] [(] _[independent]_ _[of]_ _[r]_ [)] _[,]_ _[and]_
_then_ _thresholds_ _the_ _induced_ _posterior_ P [ind] ( _Y_ = 1 _| J_ ) _at_ 1 _/_ 2 _._ _Then_ _the_ _following_ _results_ _hold:_

_1._ _**(CI**_ _**Collapses**_ _**to**_ _**the**_ _**Prior)**_ _For_ _every_ _K_ _and_ _y_ _∈{_ 0 _,_ 1 _},_ _one_ _has_ _qy_ = [1]

_**(CI**_ _**Collapses**_ _**to**_ _**the**_ _**Prior)**_ _For_ _every_ _K_ _and_ _y_ _∈{_ 0 _,_ 1 _},_ _one_ _has_ _qy_ = 2 _[.]_ _[Consequently,]_

P [ind] ( _Y_ = 1 _| J_ ) = _π_ _for_ _all_ _J,_ _so_ _gK_ [ind][(] _[J]_ [)] _[ ≡]_ **[1]** _[{][π]_ _[≥]_ [1] 2 _[}][,]_ _[and]_ _[R]_ [(] _[g]_ _K_ [ind][) = min] _[{][π,]_ [ 1] _[ −]_ _[π][}][,][ ∀][K][.]_

[1] 2 _[}][,]_ _[and]_ _[R]_ [(] _[g]_ _K_ [ind][) = min] _[{][π,]_ [ 1] _[ −]_ _[π][}][,][ ∀][K][.]_

_2._ _**(Bayes**_ _**Risk**_ _**Vanishes)**_ _Let_ _m⋆_ = _m⋆_ ( _β_ 1) _∈_ (0 _,_ 1) _denote_ _the_ _unique_ _positive_ _solution_ _to_
_m_ = tanh( _β_ 1 _m_ ) _._ _Then_ _for_ _any_ _fixed_ _threshold_ _t ∈_ (0 _, m_ [2] _⋆_ [)] _[,]_ _[the]_ _[quadratic]_ _[statistic]_ _[test:]_

_g_ ˜ _K_ ( _J_ ) := **1** _{MK_ ( _J_ ) [2] _≥_ _t},_

_MK_ ( _J_ ) = [1]

_K_

_K_

(2 _Jj_ _−_ 1) _,_

_j_ =1

_satisfies_ _R_ (˜ _gK_ ) _→_ 0 _as_ _K_ _→∞._ _Hence_ _R_ ( _gK_ _[⋆]_ [)] _[ →]_ [0] _[as]_ _[K]_ _[→∞][.]_

_3._ _**(Nonvanishing**_ _**Separation)**_ _We_ _have:_

```
        -
```

lim _R_ ( _gK_ [ind][)] _[ −]_ _[R]_ [(] _[g]_ _K_ _[⋆]_ [)] = min _{π,_ 1 _−_ _π}_ _>_ 0 _._
_K→∞_

_Proof._ We start with the proof of assertion (1).
Fix _y_ _∈{_ 0 _,_ 1 _}_ and _K_ . Under (6), the density depends on _x_ only through �� _j_ _[x][j]_ �2, and hence
is invariant under the global spin-flip _x �→−x_ :

P( _X_ = _x | Y_ = _y_ ) = P( _X_ = _−x | Y_ = _y_ ) _∀x ∈{−_ 1 _,_ +1 _}_ _[K]_ _._

Therefore, for each coordinate _r_,

E\[ _Xr_ _| Y_ = _y_ \] =

```
_xr_ P( _X_ = _x | Y_ = _y_ ) =
```

_x_ _x_

( _−xr_ ) P( _X_ = _−x | Y_ = _y_ ) = _−_ E\[ _Xr_ _| Y_ = _y_ \] _,_

_x_

so E\[ _Xr_ _|_ _Y_ = _y_ \] = 0 and hence P( _Xr_ = +1 _|_ _Y_ = _y_ ) = P( _Xr_ = _−_ 1 _|_ _Y_ = _y_ ) = [1]

so E\[ _Xr_ _|_ _Y_ = _y_ \] = 0 and hence P( _Xr_ = +1 _|_ _Y_ = _y_ ) = P( _Xr_ = _−_ 1 _|_ _Y_ = _y_ ) = 2 [.] [Since]

_Jr_ = ( _Xr_ + 1) _/_ 2, we get _qy_ = P( _Jr_ = 1 _| Y_ = _y_ ) = [1] [for] [both] _[y]_ [= 0] _[,]_ [ 1.]

_Xr_ + 1) _/_ 2, we get _qy_ = P( _Jr_ = 1 _| Y_ = _y_ ) = 2 [for] [both] _[y]_ [= 0] _[,]_ [ 1.]

With _q_ 0 = _q_ 1 = [1] [,] [the] [CI] [likelihoods] [coincide:]

[the] [CI] [likelihoods] [coincide:]
2 [,]

P [ind] ( _J_ _| Y_ = 1) = P [ind] ( _J_ _| Y_ = 0) = 2 _[−][K]_ _∀J,_

so Bayes’ rule under the CI model gives P [ind] ( _Y_ = 1 _| J_ ) = _π_ for all _J_ and _gK_ [ind][(] _[J]_ [)] _[ ≡]_ **[1]** _[{][π]_ _[≥]_ 2 [1] _[}]_ [.] [Its]

(true) misclassification risk is then

_R_ ( _gK_ [ind][) = P(] _[g]_ _K_ [ind] [=] _[ Y]_ [ ) =]

P( _Y_ = 0) = 1 _−_ _π,_ _π_ _≥_ [1]

P( _Y_ = 0) = 1 _−_ _π,_ _π_ _≥_

2 _[,]_
P( _Y_ = 1) = _π,_ _π_ _\<_ [1] _[,]_

2

[1] [= min] _[{][π,]_ [ 1] _[ −]_ _[π][}][.]_

2 _[,]_

This proves assertion (1).
Before proving assertion (2), we require some intermediate results.

33

We start by proving a magnetization representation and a uniform combinatorial bound for the
Ising model case. Fix _β_ _>_ 0 and consider the Curie-Weiss law

1 - _β_
P _β_ ( _X_ = _x_ ) =
_ZK_ ( _β_ ) [exp] 2 _K_

- - _[K]_ �2�

_xj_ _._

_j_ =1

For _m_ _∈{−_ 1 _, −_ 1 + 2 _/K, . . .,_ 1 _}_, let _NK_ ( _m_ ) be the number of configurations with magnetization
_MK_ = _m_ . Writing _r_ = # _{j_ : _xj_ = +1 _}_ = _[K]_ [(1+] 2 _[m]_ [)], we have _NK_ ( _m_ ) = - _Kr_ - and

1
P _β_ ( _MK_ = _m_ ) =
_ZK_ ( _β_ )

- _K_ - _βK_
  _K_ (1+ _m_ ) exp _,_ (27)

2 _[m]_ [2][�]

2

where _ZK_ ( _β_ ) is the corresponding normalizer (sum of the numerator over all admissible _m_ ).
Define the binary entropy (natural logs)

_H_ ( _p_ ) := _−p_ log _p −_ (1 _−_ _p_ ) log(1 _−_ _p_ ) _,_ _p ∈_ \[0 _,_ 1\] _,_

and the mean-field objective

```
 - 1 + _m_
```

Φ _β_ ( _m_ ) := _H_
2

- _[β]_ _m ∈_ \[ _−_ 1 _,_ 1\] _._

2 _[m]_ [2] _[,]_

A standard consequence of Stirling’s bounds is the uniform approximation

- - - _O_ (log _K_ ) _,_ uniformly over _m ∈_ _−_ 1 _, −_ 1 + [2] _._ (28)

_K_ _[, . . .,]_ [ 1]

- _K_
  log _K_ (1+ _m_ )

2

```
- 1 + _m_
```

= _K H_
2

Combining (27)–(28) yields

exp� _K_ Φ _β_ ( _m_ ) + _O_ (log _K_ )�
P _β_ ( _MK_ = _m_ ) = - _m_ _[′]_ [ exp] - _K_ Φ _β_ ( _m_ _[′]_ ) + _O_ (log _K_ )� _,_ (29)

where the sum runs over the ( _K_ + 1) admissible magnetization values and the _O_ (log _K_ ) term is
uniform in _m, m_ _[′]_ .
We next identify the location of the maximizers of Φ _β_ .

_[m]_ _[β]_

2 [) +] 2

**Lemma** **1.** _Let_ _β_ _>_ 0 _and_ Φ _β_ ( _m_ ) = _H_ ( [1+] _[m]_

_[β]_ _[on]_ \[[] _[−]_ [1] _[,]_ [ 1]\] _[.]_

2 _[m]_ [2]

_1._ _If_ _β_ _\<_ 1 _,_ _then_ Φ _β_ _is_ _strictly_ _concave_ _on_ ( _−_ 1 _,_ 1) _and_ _has_ _a_ _unique_ _maximizer_ _at_ _m_ = 0 _._

_2._ _If_ _β_ _>_ 1 _,_ _then_ _there_ _exists_ _a_ _unique_ _m⋆_ ( _β_ ) _∈_ (0 _,_ 1) _solving_ _m_ = tanh( _βm_ ) _._ _Moreover,_ Φ _β_ _has_
_exactly_ _two_ _global_ _maximizers_ _at_ _±m⋆_ ( _β_ ) _,_ _and_ _m_ = 0 _is_ _a_ _strict_ _local_ _minimum._

_Proof._ For _m ∈_ ( _−_ 1 _,_ 1), differentiating gives

_d_ - 1 + _m_
_dm_ _[H]_ 2

= [1]

[1]

2 [log ][1] 1 + _[ −]_ _m_ _[m]_

1 + _m_ [=] _[ −]_ [arctanh(] _[m]_ [)] _[,]_

hence
1
Φ _[′]_ _β_ [(] _[m]_ [) =] _[ −]_ [arctanh(] _[m]_ [) +] _[ βm,]_ Φ _[′′]_ _β_ [(] _[m]_ [) =] _[ −]_ [+] _[ β.]_
1 _−_ _m_ [2]

If _β_ _\<_ 1, then for all _m ∈_ ( _−_ 1 _,_ 1),

Φ _[′′]_ _β_ [(] _[m]_ [)] _[ ≤−]_ [1 +] _[ β]_ _[\<]_ [ 0]

34

(since 1 _/_ (1 _−_ _m_ [2] ) _≥_ 1), so Φ _β_ is strictly concave and has at most one critical point. Because Φ _β_ is
even, Φ _[′]_ _β_ [(0) = 0,] [so] _[m]_ [ = 0] [is] [the] [unique] [maximizer.]
If _β_ _>_ 1, then Φ _[′′]_ _β_ [(0)] [=] _[β][ −]_ [1] _[>]_ [0,] [so] _[m]_ [=] [0] [is] [a] [strict] [local] [minimum.] [Critical] [points] [satisfy]
Φ _[′]_ _β_ [(] _[m]_ [)] [=] [0,] [i.e.] [arctanh(] _[m]_ [)] [=] _[βm]_ [,] [equivalently] _[m]_ [=] [tanh(] _[βm]_ [).] [Define] _[f]_ [(] _[m]_ [)] [:=] [tanh(] _[βm]_ [)] _[ −]_ _[m]_
on \[0 _,_ 1\]. Then _f_ (0) = 0 and _f_ _[′]_ (0) = _β_ _−_ 1 _>_ 0, while _f_ (1) = tanh( _β_ ) _−_ 1 _\<_ 0. By continuity,
there exists at least one root in (0 _,_ 1). Moreover, _f_ _[′]_ ( _m_ ) = _β_ (1 _−_ tanh [2] ( _βm_ )) _−_ 1 = _β_ (1 _−_ _m_ [2] ) _−_ 1
at a root (since then tanh( _βm_ ) = _m_ ), and _m �→_ _β_ (1 _−_ _m_ [2] ) _−_ 1 is strictly decreasing on \[0 _,_ 1\]. This
implies _f_ is strictly concave on any interval where it is positive and strictly decreasing once _m_ is
large enough; in particular, _f_ can cross zero at most once in (0 _,_ 1), so the positive root is unique;
call it _m⋆_ ( _β_ ). By symmetry, _−m⋆_ ( _β_ ) is also a critical point.
At _m_ = _±m⋆_ ( _β_ ), we have _β_ (1 _−_ _m_ [2] _⋆_ [(] _[β]_ [))] _[\<]_ [1] [(equivalently] [the] [slope] [of] [tanh(] _[βm]_ [)] [at] [the] [in-]
tersection is _\<_ 1), so Φ _[′′]_ _β_ [(] _[±][m][⋆]_ [(] _[β]_ [))] [=] _[−]_ 1 _−m_ 1 _⋆_ ( _β_ ) [2] [+] _[β]_ _[\<]_ [0,] [hence] _[±][m][⋆]_ [(] _[β]_ [)] [are] [strict] [local] [max-]
ima. Since Φ _β_ is continuous on compact \[ _−_ 1 _,_ 1\], it attains global maxima; the only candidates
are critical points and endpoints. The endpoints satisfy _H_ ( [1] _[±]_ [1] [=] [0,] [hence] [Φ] _[β]_ [(] _[±]_ [1)] [=] _[β]_ [while]

2 [)] 2 [,]

Φ _β_ ( _±m⋆_ ( _β_ )) _>_ Φ _β_ (0) = log 2 for _β_ _>_ 1 (indeed _±m⋆_ ( _β_ ) are maxima and 0 is a local minimum).
Thus the global maxima are exactly _±m⋆_ ( _β_ ).

We next show exponential concentration of _MK_ under _β_ 0 and _β_ 1. Our approach for proving
concentration for Curie-Weiss models is motivated by Friedli and Velenik [16, Chapter 2]. While
more sophisticated approaches are available to obtain sharp concentration bounds, we use this
simpler approach as a coarse concentration result suffices to prove our separation result of interest.

**Lemma** **2** (Concentration under _β_ _\<_ 1) **.** _Fix_ _β_ _∈_ (0 _,_ 1) _and_ _δ_ _∈_ (0 _,_ 1) _._ _Then_ _there_ _exists_ _c_ =
_c_ ( _β, δ_ ) _>_ 0 _such_ _that_

P _β_ - _|MK| ≥_ _δ_ - _≤_ exp( _−cK_ ) _for_ _all_ _sufficiently_ _large_ _K._

_Proof._ By assertion (1) of Lemma 1, Φ _β_ has unique maximizer at 0. By continuity of Φ _β_ and
compactness of _{m ∈_ \[ _−_ 1 _,_ 1\] : _|m| ≥_ _δ}_,

∆:= Φ _β_ (0) _−_ sup Φ _β_ ( _m_ ) _>_ 0 _._
_|m|≥δ_

Using (29), for the numerator we bound

- exp� _K_ Φ _β_ ( _m_ ) + _O_ (log _K_ )� _≤_ ( _K_ + 1) exp� _K_ sup Φ _β_ ( _m_ ) + _O_ (log _K_ )� _,_

_|m|≥δ_
_|m|≥δ_

and for the denominator,

- exp� _K_ Φ _β_ ( _m_ _[′]_ ) + _O_ (log _K_ )� _≥_ exp� _K_ Φ _β_ (0) _−_ _O_ (log _K_ )� _._

_m_ _[′]_

Taking the ratio gives

P _β_ ( _|MK| ≥_ _δ_ ) _≤_ ( _K_ + 1) exp� _−_ _K_ ∆+ _O_ (log _K_ )� = exp� _−_ _K_ ∆+ _O_ (log _K_ )� _,_

which is _≤_ exp( _−cK_ ) for all large _K_ for any _c \<_ ∆.

**Lemma** **3** (Concentration under _β_ _>_ 1) **.** _Fix_ _β_ _>_ 1 _and_ _let_ _m⋆_ = _m⋆_ ( _β_ ) _∈_ (0 _,_ 1) _be_ _the_ _unique_
_positive_ _solution_ _to_ _m_ = tanh( _βm_ ) _._ _For_ _any_ _ε ∈_ (0 _, m⋆_ ) _,_ _there_ _exists_ _c_ = _c_ ( _β, ε_ ) _>_ 0 _such_ _that_

P _β_ ��� _|MK| −_ _m⋆_ �� _≥_ _ε_ - _≤_ exp( _−cK_ ) _for_ _all_ _sufficiently_ _large_ _K._

35

_Proof._ By Lemma 1(2), Φ _β_ has exactly two strict global maximizers at _±m⋆_ . Define the closed set

_Fε_ := _{m ∈_ \[ _−_ 1 _,_ 1\] : �� _|m| −_ _m⋆_ �� _≥_ _ε}._

Since _±m⋆_ _∈/_ _Fε_ and Φ _β_ is continuous, compactness implies

∆:= Φ _β_ ( _m⋆_ ) _−_ sup Φ _β_ ( _m_ ) _>_ 0 _._
_m∈Fε_

The same numerator/denominator bounding argument used in Lemma 2 applied to the event
_{MK_ _∈_ _Fε}_ yields

P _β_ ( _MK_ _∈_ _Fε_ ) _≤_ ( _K_ + 1) exp� _−_ _K_ ∆+ _O_ (log _K_ )� = exp� _−_ _K_ ∆+ _O_ (log _K_ )� _≤_ exp( _−cK_ )

for any _c \<_ ∆and all sufficiently large _K_ .

We are now ready the prove assertion (2).
Consider the joint model from Theorem 1 with _β_ 0 _∈_ (0 _,_ 1) and _β_ 1 _>_ 1. Fix any _t ∈_ (0 _, m⋆_ ( _β_ 1) [2] )
and define _g_ ˜ _K_ ( _J_ ) = **1** _{MK_ ( _J_ ) [2] _≥_ _t}_ .
_T√ype_ _I_ _error_ _under_ _Y_ = 0 _:_ Conditional on _Y_ = 0, the spins follow P _β_ 0, hence by Lemma 2 with
_δ_ = _t_,

_t_,
_√_
P(˜ _gK_ = 1 _| Y_ = 0) = P _β_ 0( _MK_ [2] _[≥]_ _[t]_ [) = P] _[β]_ 0 [(] _[|][M][K][| ≥]_

_t_ ) _−→_ 0 _._

_Type_ _II_ _error√_ _under_ _Y_ = 1 _:_ Conditional on _√Y_ = 1, the spins follow P _β_ 1. Let _m⋆_ = _m⋆_ ( _β_ 1) and
set _ε_ := _[m][⋆][−]_ _t_ _>_ 0. If _M_ [2] _[\<]_ _[t]_ [,] [then] _[|][M][K][|]_ _[\<]_ _t_ = _m⋆_ _−_ 2 _ε_, hence �� _|MK| −_ _m⋆_ �� _≥_ 2 _ε_ . Therefore,

_√_ _√_

_[−]_ 2 _t_ _>_ 0. If _MK_ [2] _[\<]_ _[t]_ [,] [then] _[|][M][K][|]_ _[\<]_

set _ε_ := _[m][⋆][−]_ 2 _t_ _>_ 0. If _MK_ [2] _[\<]_ _[t]_ [,] [then] _[|][M][K][|]_ _[\<]_ _t_ = _m⋆_ _−_ 2 _ε_, hence �� _|MK| −_ _m⋆_ �� _≥_ 2 _ε_ . Therefore,

by Lemma 3 (applied with 2 _ε_ ),

P(˜ _gK_ = 0 _| Y_ = 1) = P _β_ 1( _MK_ [2] _[< t]_ [)] _[ ≤]_ [P] _[β]_ 1��� _|MK| −_ _m⋆_ �� _≥_ 2 _ε_ - _−→_ 0 _._

Combining the two conditional errors,

_R_ (˜ _gK_ ) = _π_ P(˜ _gK_ = 0 _| Y_ = 1) + (1 _−_ _π_ ) P(˜ _gK_ = 1 _| Y_ = 0) _−→_ 0 _._

Since the Bayes predictor _gK_ _[⋆]_ [minimizes] [misclassification] [risk] [under] [the] [true] [joint] [law,]

_R_ ( _gK_ _[⋆]_ [)] _[ ≤]_ _[R]_ [(˜] _[g][K]_ [)] _[ →]_ [0] _[,]_

proving assertion (2).
Finally, we immediately have the separation limit stated in assertion (3). Indeed, assertion (1)
gives _R_ ( _gK_ [ind][) = min] _[{][π,]_ [ 1] _[ −]_ _[π][}]_ [for] [all] _[K]_ [,] [while] [assertion] [(2)] [gives] _[R]_ [(] _[g]_ _K_ _[⋆]_ [)] _[ →]_ [0.] [Hence]

lim
_K→∞_

- _R_ ( _gK_ [ind][)] _[ −]_ _[R]_ [(] _[g]_ _K_ _[⋆]_ [)] = min _{π,_ 1 _−_ _π} −_ 0 = min _{π,_ 1 _−_ _π} >_ 0 _._

This proves assertion (3) and completes the overall proof.

**E.2** **Proof** **of** **Theorem** **2**

**Theorem** **2** (Curie-Weiss separation with informative marginals) **.** _Let_ _Y_ _∈{_ 0 _,_ 1 _}_ _with_ P( _Y_ =

1. = _π_ _∈_ (0 _,_ 1) _._ _For_ _each_ _K_ _≥_ 1 _,_ _define_ _spins_ _X_ = ( _X_ 1 _, . . ., XK_ ) _∈{−_ 1 _,_ +1 _}_ _[K]_ _and_ _votes_
   _Jj_ = ( _Xj_ + 1) _/_ 2 _∈{_ 0 _,_ 1 _}._ _Let_ _the_ _class-conditional_ _laws_ _of_ _X_ _be_ _Curie-Weiss_ _models_ _with_ _(possibly_
   _K-dependent)_ _external_ _fields:_

_K_

-

_xj_ _,_ (7)

_j_ =1

1 - _βy_
P( _X_ = _x | Y_ = _y_ ) = exp

2 _K_
_ZK_ [(] _[y]_ [)]

- - _[K]_ �2

_xj_ + _hy,K_

_j_ =1

_for_ _y_ _∈{_ 0 _,_ 1 _}._ _Assume_ _parameters_ _satisfy:_

36

_1._ _(High-temperature_ _Class)_ _β_ 0 _∈_ (0 _,_ 1) _and_ _h_ 0 _,K_ _≡_ _h_ 0 _\<_ 0 _is_ _a_ _fixed_ _negative_ _constant;_

_2._ _(Low-temperature_ _Class_ _with_ _Weak_ _Symmetry_ _Breaking)_ _β_ 1 _>_ 1 _and_ _h_ 1 _,K_ = _c/K_ _with_ _some_
_fixed_ _c >_ 0 _._

_Let_ _MK_ := _K_ [1] - _Kj_ =1 _[X][j]_ _[∈]_ \[[] _[−]_ [1] _[,]_ [ 1]\] _[be]_ _[the]_ _[magnetization.]_ _[Let]_ _[m]_ [0] _[∈]_ [(] _[−]_ [1] _[,]_ [ 0)] _[be]_ _[the]_ _[unique]_ _[solution]_ _[of]_

_the_ _mean-field_ _equation_ _m_ 0 = tanh( _β_ 0 _m_ 0 + _h_ 0) _,_ _and_ _let_ _m⋆_ = _m⋆_ ( _β_ 1) _∈_ (0 _,_ 1) _be_ _the_ _unique_ _positive_
_solution_ _of_ _m⋆_ = tanh( _β_ 1 _m⋆_ ) _._ _Define_

_e_ _[cm][⋆]_ - 1 _p_ := _,_

_e_ _[cm][⋆]_ + _e_ _[−][cm][⋆]_ [=] _[ σ]_ [(2] _[cm][⋆]_ [)] _[ ∈]_ 2 _[,]_ [ 1]

_q_ 0 := P( _J_ 1 = 1 _| Y_ = 0) = [1 +] _[ m]_ [0]

_[ m]_ [0]
_∈_ 0 _,_ [1]
2 2

2

_,_

```
             - 1
```

_q_ 1 := P( _J_ 1 = 1 _| Y_ = 1) = [1 + (2] _[p][ −]_ [1)] _[m][⋆]_ _∈_ _._

2 2 _[,]_ [ 1]

_Assume_ _additionally_ _that_

1 _−_ _m⋆_

_< q_ 0 _⇐⇒_ _m⋆_ _>_ 1 _−_ 2 _q_ 0 _._ (8)
2

_Let_ _gK_ _[⋆]_ _[denote]_ _[the]_ _[Bayes]_ _[predictor]_ _[under]_ _[the]_ _[true]_ _[model]_ [(7)] _[.]_ _[Let]_ _[g]_ _K_ [ind] _denote_ _the_ _population_ _CI-_
_predictor that replaces_ P( _J_ _| Y_ = _y_ ) _by the product of the true marginals_ [�] _j_ _[K]_ =1 _[q]_ _y_ _[J][j]_ [(1] _[−][q]_ _y_ [)][1] _[−][J][j]_ _[.Then,]_
_the_ _following_ _hold:_

_1._ _**(Informative**_ _**Marginals)**_ _Each_ _judge_ _is_ _individually_ _better_ _than_ _random:_ _q_ 0 _\<_ 21 _[\<]_ _[q]_ [1]
_(equivalently,_ _specificity_ 1 _−_ _q_ 0 _>_ [1] _[and]_ _[sensitivity]_ _[q]_ [1] _[>]_ [1] _[).]_

[1] 2 _[and]_ _[sensitivity]_ _[q]_ [1] _[>]_ [1] 2

2 _[).]_

_2._ _**(Bayes**_ _**Risk**_ _**Vanishes)**_ _For_ _any_ _fixed_ _threshold_ _t_ _satisfying_ _|m_ 0 _| < t < m⋆,_ _the_ _aggregator_
_g_ ˜ _K_ ( _J_ ) := **1** _{|MK| ≥_ _t}_ _has_ _R_ (˜ _gK_ ) _→_ 0 _as_ _K_ _→∞._ _Consequently,_ _R_ ( _gK_ _[⋆]_ [)] _[ →]_ [0] _[.]_

_3._ _**(CI**_ _**Remains**_ _**Bounded**_ _**away**_ _**from**_ _**Bayes)**_ _As_ _K_ _→∞,_ _we_ _have_ _R_ ( _gK_ [ind][)] _[→]_ _[π]_ [(1] _[ −]_ _[p]_ [)] _[,]_
_and_ _hence_ lim _K→∞_ - _R_ ( _gK_ [ind][)] _[ −]_ _[R]_ [(] _[g]_ _K_ _[⋆]_ [)] - _≥_ _π_ (1 _−_ _p_ ) _>_ 0 _._

_Proof._ The proof is similar to that of Theorem 1. We start with the magnetization representation.
For _β_ _>_ 0 and field _h_, the Curie-Weiss probability of _MK_ = _m_ (with _m_ _∈{−_ 1 _, −_ 1 + _K_ [2] _[, . . .,]_ [ 1] _[}]_ [)]

can be written as

- _βK_ exp _,_ (30)
  2 _[m]_ [2][ +] _[ hKm]_

1
P _β,h_ ( _MK_ = _m_ ) =
_ZK_ ( _β, h_ )

- _K_
  _K_ (1+ _m_ )

2

where _ZK_ ( _β, h_ ) normalizes the mass over all admissible _m_ . Let _H_ ( _p_ ) = _−p_ log _p −_ (1 _−_ _p_ ) log(1 _−_ _p_ )
and define

```
          - 1 + _m_               Φ _β_ ( _m_ ) := _H_ + _[β]_ _m ∈_ [ _−_ 1 _,_ 1] _._
```

2 2 _[m]_ [2] _[,]_

- _[β]_

_m ∈_ \[ _−_ 1 _,_ 1\] _._
2 _[m]_ [2] _[,]_

Stirling’s formula yields

```
     -          _K_          - 1 + _m_
```

log _K_ (1+ _m_ ) = _K H_

2

2

uniformly over admissible _m_, hence

- _O_ (log _K_ ) _,_

  ```
    -         P _β,h_ ( _MK_ = _m_ ) _∝_ exp _K_ Φ _β_ ( _m_ ) + _hKm_ + _O_ (log _K_ ) _._ (31)
  ```

37

We now compute the marginals correponding to item (1). By exchangeability, E\[ _X_ 1 _| Y_ = _y_ \] =
E\[ _MK_ _| Y_ = _y_ \]. Under ( _β_ 0 _, h_ 0) with _β_ 0 _∈_ (0 _,_ 1) and fixed _h_ 0 _\<_ 0, the standard mean-field analysis
implies that _MK_ _→_ _m_ 0 in probability, where _m_ 0 is the unique solution to _m_ = tanh( _β_ 0 _m_ + _h_ 0).
Hence E\[ _MK_ _| Y_ = 0\] _→_ _m_ 0 _\<_ 0 and

_[|][ Y]_ [= 0]\]
_q_ 0 = P( _J_ 1 = 1 _| Y_ = 0) = P( _X_ 1 = +1 _| Y_ = 0) = [1 +][ E]\[[] _[X]_ [1]

_[ m]_ [0]

_\<_ [1]
2 2

_[|][ Y]_ [= 0]\]

_→_ [1 +] _[ m]_ [0]
2 2

2 _[.]_

Under ( _β_ 1 _, h_ 1 _,K_ ) with _β_ 1 _>_ 1 and _h_ 1 _,K_ = _c/K_, we show below (Step 2) that _MK_ converges in
distribution to a two-point mixture _p δm⋆_ + (1 _−_ _p_ ) _δ−m⋆_ with _p_ = _σ_ (2 _cm⋆_ ) _∈_ (1 _/_ 2 _,_ 1). Therefore
E\[ _MK_ _| Y_ = 1\] _→_ (2 _p −_ 1) _m⋆_ _>_ 0 and

_[|][ Y]_ [= 1]\]
_q_ 1 = P( _J_ 1 = 1 _| Y_ = 1) = [1 +][ E]\[[] _[X]_ [1]

_[ −]_ [1)] _[m][⋆]_

_>_ [1]
2 2

_[|][ Y]_ [= 1]\]

_→_ [1 + (2] _[p][ −]_ [1)] _[m][⋆]_
2 2

2 _[.]_

This proves item (1).
We now examine the magnetization limits under the two classes. Consider _Y_ = 0. Since
_β_ 0 _\<_ 1, Φ _β_ 0 is strictly concave on ( _−_ 1 _,_ 1) and has a unique maximizer; adding the linear term
_h_ 0 _m_ preserves uniqueness. Thus the exponent in (31) has a unique global maximizer at _m_ 0, and a
standard Laplace argument yields

P
_MK_ _−−−−→_ (32)
_K→∞_ _[m]_ [0] _[.]_

Now consider _Y_ = 1. Here _h_ 1 _,K_ = _c/K_, so _h_ 1 _,KK_ = _c_ and (31) becomes

```
              -                  P( _MK_ = _m | Y_ = 1) _∝_ exp _K_ Φ _β_ 1( _m_ ) + _cm_ + _O_ (log _K_ ) _._ (33)
```

For _β_ 1 _>_ 1, Φ _β_ 1 has exactly two global maximizers at _±m⋆_ (where _m⋆_ = tanh( _β_ 1 _m⋆_ )). Fix
_ε ∈_ (0 _, m⋆_ ) and define neighborhoods

_U_ + := \[ _m⋆_ _−_ _ε, m⋆_ + _ε_ \] _,_ _U−_ := \[ _−m⋆_ _−_ _ε, −m⋆_ + _ε_ \] _,_ _Fε_ := \[ _−_ 1 _,_ 1\] \_\_ ( _U_ + _∪_ _U−_ ) _._

By continuity and strict maximality at _±m⋆_, there exists ∆( _ε_ ) _>_ 0 such that sup _m∈Fε_ Φ _β_ 1( _m_ ) _≤_
Φ _β_ 1( _m⋆_ ) _−_ ∆( _ε_ ). Using (33) and the same numerator/denominator bounding argument as in
Lemma 3, we obtain exponential concentration:

P� _MK_ _∈_ _Fε_ _| Y_ = 1� _≤_ _e_ _[−][c]_ [1] _[K]_ for some _c_ 1 = _c_ 1( _ε_ ) _>_ 0 _._ (34)

Hence _|MK| →_ _m⋆_ in probability under _Y_ = 1.
It remains to identify the limiting _mixture_ _weights_ . Let _AK,_ + (resp. _AK,−_ ) denote the total
unnormalized mass in _U_ + (resp. _U−_ ) in (33). On _U_ + we have _m_ = _m⋆_ + _o_ (1) and on _U−_ we have
_m_ = _−m⋆_ + _o_ (1), while Φ _β_ 1( _m_ ) = Φ _β_ 1( _m⋆_ ) + _o_ (1) in both neighborhoods. Therefore

# _AK,_ +

_AK,−_

- _m∈U_ + [exp] - _K_ Φ _β_ 1( _m_ ) + _cm_ + _O_ (log _K_ )�

- _m∈U−_ [exp] - _K_ Φ _β_ 1( _m_ ) + _cm_ + _O_ (log _K_ )� _−→_ exp(2 _cm⋆_ ) _,_

because the leading _K_ Φ _β_ 1( _m⋆_ ) contributions cancel and the remaining _cm_ term evaluates to _±cm⋆_ .
Combining with (34) implies

_e_ _[cm][⋆]_
P( _MK_ _>_ 0 _| Y_ = 1) _→_ P( _MK_ _\<_ 0 _| Y_ = 1) _→_ 1 _−_ _p,_

_e_ _[cm][⋆]_ + _e_ _[−][cm][⋆]_ [=] _[ p,]_

38

and thus _MK_ _⇒_ _p δm⋆_ + (1 _−_ _p_ ) _δ−m⋆_ under _Y_ = 1.
We are now in the position to show that Bayes risk vanishes, as claimed in item (2). Pick any
_t_ with _|m_ 0 _|_ _\<_ _t_ _\<_ _m⋆_ and define _g_ ˜ _K_ ( _J_ ) = **1** _{|MK|_ _≥_ _t}_ . Under _Y_ = 0, (32) implies _|MK|_ _\<_ _t_
with probability _→_ 1. Under _Y_ = 1, (34) implies _|MK|_ _>_ _t_ with probability _→_ 1. Therefore
P(˜ _gK_ = _Y_ ) _→_ 0, i.e. _R_ (˜ _gK_ ) _→_ 0. Since _gK_ _[⋆]_ [minimizes] [risk,] _[R]_ [(] _[g]_ _K_ _[⋆]_ [)] _[ ≤]_ _[R]_ [(˜] _[g][K]_ [)] _[ →]_ [0.]
Next, we move on to proving item (3). Under the CI model with marginals ( _q_ 0 _, q_ 1), the (oracle)
CI log-likelihood ratio depends only on _SK_ = [�] _j_ _[K]_ =1 _[J][j]_ [or] [equivalently] _[s][K]_ [=] _[ S][K][/K]_ [:]

_[|][ Y]_ [= 1)]
log [P][ind][(] _[J]_

_[q]_ [1] + (1 _−_ _sK_ ) log [1] _[ −]_ _[q]_ [1]

_q_ 0 1 _−_ _q_ 0

1 _−_ _q_ 0

_[|][ Y]_ [= 1)]
[P][ind][(] _[J]_ _sK_ log _[q]_ [1]

Pind( _J_ _| Y_ = 0) [=] _[ K]_ _q_ 0

_._

Since _q_ 1 _>_ _q_ 0, the function of _s_ in parentheses is strictly increasing and has a unique root _s_ thr _∈_
( _q_ 0 _, q_ 1). Thus the CI-predictor satisfies (for all large _K_, ignoring the vanishing prior term at scale
_K_ )
_gK_ [ind][(] _[J]_ [) =] **[ 1]** _[{][s][K]_ _[≥]_ _[s]_ [thr] _[}][.]_

Under _Y_ = 0, we have _sK_ = (1 + _MK_ ) _/_ 2 _→_ (1 + _m_ 0) _/_ 2 = _q_ 0 _\<_ _s_ thr in probability, so P( _gK_ [ind] = 1 _|_
_Y_ = 0) _→_ 0.
Under _Y_ = 1, we have _sK_ _→_ (1 _± m⋆_ ) _/_ 2 depending on the phase. By (8), the negative-phase
limit (1 _−_ _m⋆_ ) _/_ 2 is strictly smaller than _q_ 0 _\<_ _s_ thr, so _gK_ [ind] _→_ 0 on the negative phase; while
(1 + _m⋆_ ) _/_ 2 _> s_ thr so _gK_ [ind] _[→]_ [1] [on] [the] [positive] [phase.] [Therefore]

P( _gK_ [ind] [= 0] _[ |][ Y]_ [= 1)] _[ →]_ [P(negative] [phase] _[ |][ Y]_ [= 1) = 1] _[ −]_ _[p,]_

and hence

_R_ ( _gK_ [ind][) =] _[ π]_ [ P(] _[g]_ _K_ [ind] [= 0] _[ |][ Y]_ [= 1) + (1] _[ −]_ _[π]_ [) P(] _[g]_ _K_ [ind] [= 1] _[ |][ Y]_ [= 0)] _[ →]_ _[π]_ [(1] _[ −]_ _[p]_ [)] _[.]_

Together with _R_ ( _gK_ _[⋆]_ [)] _[ →]_ [0,] [this] [yields] [the] [claimed] [nonvanishing] [excess-risk] [lower] [bound.]

### **F Numerical Simulations**

**F.1** **CI** **Judges:** **Uniform** **vs.** **Weighted** **Majority** **Vote**

We present sanity-check experiment in the _conditionally_ _independent_ (CI) setting, where the classical Dawid-Skene family is well-specified. Each item has a latent label _Yi_ _∈{_ 0 _,_ 1 _}_ and _K_ = 6 judges
produce independent votes _Jij_ _∈{_ 0 _,_ 1 _}_ conditional on _Yi_ . Judge _j_ is characterized by sensitivity
_αj_ = P( _Jij_ = 1 _|_ _Yi_ = 1) and specificity _βj_ = P( _Jij_ = 0 _|_ _Yi_ = 0). For each setup we generate
_n_ = 200 items from the CI model with the _true_ ( _α, β_ ) listed in Table 2. We consider four setups
spanning strong annotators (Setup 1) and heterogeneous, partially unreliable annotators (Setups 2–
4). We evaluate two aggregation rules: (i) Uniform majority vote (Uniform MV), which predicts
the class supported by a strict majority of votes, and (ii) Weighted majority vote learned by the
EM approach in Algorithm 1, where we fit the asymmetric CI model with Beta priors on ( _αj, βj_ )
and then apply the induced Bayes-optimal linear rule (equivalently, a weighted vote with weights
given by the estimated log-odds contributions of each judge.
Table 3 reports average 0–1 accuracy across runs for each setup. Two trends are consistent with
theory. First, when all judges are strong and roughly exchangeable (Setup 1), uniform MV is already
near-optimal and EM-based weighting provides only a small gain. Second, in the heterogeneous
regimes (Setups 2–4), uniform MV can substantially underperform because it treats all judges
as equally informative and ignores asymmetric error patterns. In contrast, CI-WMV learns to

39

True sensitivities True specificities
Setup _α_ 1 _α_ 2 _α_ 3 _α_ 4 _α_ 5 _α_ 6 _β_ 1 _β_ 2 _β_ 3 _β_ 4 _β_ 5 _β_ 6

#1 0.90 0.90 0.90 0.90 0.90 0.90 0.90 0.90 0.90 0.95 0.90 0.95
#2 0.26 0.53 0.64 0.50 0.67 0.70 0.34 0.54 0.65 0.76 0.70 0.30
#3 0.26 0.30 0.24 0.50 0.70 0.80 0.80 0.90 0.50 0.60 0.37 0.23
#4 0.60 0.63 0.74 0.75 0.67 0.80 0.70 0.59 0.95 0.86 0.77 0.83

Table 2: True per-judge sensitivities and specificities used in the CI simulations ( _K_ = 6 judges).

Setup CI-WMV (via EM) CI-UMV

Table 3: Comparing Weighted Majority Vote (CI-WMV) where the weights are learned via EM
and Uniform Majority Vote under Conditionally (CI-UMV) independent judges with parameters
represented in Table 2. Reported numbers represent the average accuracy over 20 trials.

up-weight reliable judges and down-weight weak (or effectively adversarial) ones, yielding large
improvements: in Setup 2 accuracy increases from 0.597 to 0.726, and in Setup 3 from 0.520 to
0.611. Even in Setup 4, where most judges are reasonably informative but still heterogeneous, CIWMV improves over uniform MV (0.930 vs. 0.917). Overall, these CI experiments establish a strong
baseline: when conditional independence holds, learned weighted aggregation offers meaningful
gains over uniform majority vote whenever annotator quality is non-uniform, and it recovers nearceiling performance when all annotators are strong.

**F.2** **Dependent** **Judges:** **Ising/Factor** **models** **vs.** **Weighted** **Majority** **Voting**

We next evaluate aggregation under _dependent_ judges, where the conditional-independence (CI)
is misspecified. Across the experiments below, the goal is to compare a strong CI baseline,—
Weighted MV learned by EM under the asymmetric CI model—Class-dependent Ising with classspecific couplings and factor models. All methods are trained in an unsupervised manner using the
generalized-EM framework (Algorithm 1); for Ising models we use pseudo-likelihood in the M-step
and approximate class scores in the E-step.
**Simulation** **Setup** **1** **(Illustrating** **Theorem** **2).** To empirically illustrate the Curie-Weiss
separation with _informative_ marginals, we generate synthetic vote vectors from the class-conditional
Curie-Weiss model (7) and compare the CI-predictors _gK_ [ind] to the dependence-aware (near-Bayes)
rule _g_ ˜ _K_ ( _J_ ) = **1** _{|MK|_ _≥_ _t}_ suggested by the proof. We fix ( _π, β_ 0 _, h_ 0) with _β_ 0 _∈_ (0 _,_ 1) and _h_ 0 _\<_ 0,
and vary the low-temperature parameters ( _β_ 1 _, c_ ) with _β_ 1 _>_ 1 and _c_ _>_ 0; for each pair we set
_h_ 1 _,K_ = _c/K_ and compute _m_ 0 and _m⋆_ ( _β_ 1) from the mean-field equations. We restrict to parameter
settings satisfying the separation condition (8) and choose a threshold _t_ _∈_ ( _|m_ 0 _|, m⋆_ ) (e.g., _t_ =
( _|m_ 0 _|_ + _m⋆_ ) _/_ 2). For each ( _β_ 1 _, c, K_ ) we sample _n_ i.i.d. items: draw _Y_ _∼_ Bernoulli( _π_ ), then draw
spins _X_ _∈{±_ 1 _}_ _[K]_ from (7) (e.g., via Glauber dynamics with burn-in), and finally map to votes
_Jj_ = ( _Xj_ +1) _/_ 2. We evaluate (i) the empirical risk (denoted by _R_ [ˆ] ) of _g_ ˜ _K_ (a proxy for Bayes, which
should approach 0 as _K_ grows) and (ii) the empirical risk of the _oracle_ CI-predictor _gK_ [ind][,] [which]
uses the true marginals _q_ 0 _, q_ 1 to form the naive-Bayes log-likelihood ratio in _SK_ = [�] _j_ _[J][j]_ [.] [The]

40

results are shown in Figure 4. The plots, directly mirror the theorem’s message: _R_ [�] (˜ _gK_ ) rapidly
decreases with _K_, while _R_ [�] ( _gK_ [ind][)] [approaches] [a] [positive] [constant] [that] [varies] [smoothly] [with] [(] _[β]_ [1] _[, c]_ [)]
through _π_ (1 _−_ _p_ ).
**Simulation Setup 2 (Illustrating Theorem 3).** To empirically illustrate the asymptotic separation under the exchangeable latent-factor model (21), we simulate votes from the generative process
with fixed parameters ( _π, a, b, λ, σZ_ [2] [)] [and] [vary] _[λ]_ [and/or] _[σ]_ _Z_ [2] [while] [increasing] [the] [number] [of] [judges]
_K_ . For each run, we draw _n_ independent items: sample _Yi_ _∼_ Bernoulli( _π_ ) and _Zi_ _∼N_ (0 _, σZ_ [2] [),]

then draw votes _Ji_ 1 _, . . ., JiK_ _|_ ( _Yi, Zi_ ) [iid] _∼_ Bernoulli( _p_ ( _Yi, Zi_ )). We evaluate two plug-in aggregators based on the empirical vote fraction _siK_ = _K_ _[−]_ [1][ �] _[K]_ _j_ =1 _[J][ij]_ [:] [the] [Bayes-optimal] [prediction] [rule]
_g∞_ _[⋆]_ [(] _[J][i]_ [) =] **[1]** _[{][ℓ][⋆]_ [(] _[s][i][∞]_ [)] _[≥]_ [0] _[}]_ [(approximated] [by] [using] _[s][iK]_ [in] [place] [of] _[s][i][∞]_ [),] [and] [the] [CI-prediction] [rule]
_g∞_ [ind][(] _[J][i]_ [)] [=] **[1]** _[{][ℓ]_ [ind][(] _[s][i][∞]_ [)] _[≥]_ [0] _[}]_ [(again] [approximated] [using] _[s][iK]_ [),] [where] _[q][y]_ [=] [E] _[Z]_ \[[] _[p]_ [(] _[y, Z]_ [)]\] [is] [computed]
numerically. To visualize the separation predicted by the theorem, we again plot in Figure 5: (i)
the empirical risks _R_ ( _gK_ _[⋆]_ [)] [and] _[R]_ [(] _[g]_ _K_ [ind][)] [versus] _[K]_ [for] [different] [values] [of] _[λ]_ [and] _[σ]_ _Z_ [2] [),] [and] [(ii)] [the]
empirical separation. These plots highlight the theorem’s message: under dependence (larger _|λ|_
or _σZ_ [2] [), the disagreement event] _[ {][g]_ _∞_ [ind] [=] _[ g]_ _∞_ _[⋆]_ _[}]_ [ typically expands, and the separation becomes nonzero.]

30

20

10

0

30

20

10

0

50 100 150 200 250 300
Number of Judges

50 100 150 200 250 300
Number of Judges

50 100 150 200 250 300
Number of Judges

50 100 150 200 250 300
Number of Judges

30

25

20

34

32

30

28

Figure 4: Ising predictors (Class-Dep. Ising) versus CI-predictors (CI-WMV): The plots on the left
and right represent the empirical risk and empirical separation respectively. Top row corresponds to
_β_ 1 = 2 _, c_ = 1 _._ 5. Bottom row corresponds to _β_ 1 = 5 _, c_ = 1. For all plots, _π_ = 0 _._ 7 _, β_ 0 = 0 _._ 5 _, h_ 0 = _−_ 0 _._ 5
and _n_ = 1000. The standard errors are of small width, although they are plotted.

Across both dependent judges cases—dependence induced by latent factors and dependence
induced by Curie-Weiss interactions—CI based Weighted Majority Voting aggregation rule underperforms the respective posteriors.

41

30

25

20

15

10

5

0

35

30

25

20

15

10

5

50 100 150 200 250 300
Number of Judges

50 100 150 200 250 300
Number of Judges

50 100 150 200 250 300
Number of Judges

50 100 150 200 250 300
Number of Judges

30.0

27.5

25.0

22.5

20.0

17.5

30.0

27.5

25.0

22.5

20.0

17.5

15.0

Figure 5: Latent-factor (Factor) predictor versus CI-predictors (CI-WMV). The plots on the left
and right represent the empirical risk and empirical separation respectively. Top row corresponds
to _|λ|_ = 0 _._ 1 _, σZ_ [2] [=] [1.] [Bottom] [row] [corresponds] [to] _[|][λ][|]_ [=] [0] _[.]_ [15] _[, σ]_ _Z_ [2] [=] [1] _[.]_ [5.] [For] [all] [plots,] _[π]_ [=] [0] _[.]_ [7] _[, a]_ [=]
0 _._ 5 _, b_ = 1 and _n_ = 1000. The standard errors are of small width, although they are plotted.

### **G Additional Details on Real Datasets**

**G.1** **Preprocessing** **of** **WikiQA** **Dataset**

In Tables 4 and 5, we present the examples of two questions from the WikiQA dataset along with
the corresponding candidate answers. In the former case, there exists a correct answer among the
candidate ones, therefore, we label a concatenated text chunk as relevant. In the latter case, none
of the candidate answers is correct, therefore. we label a concatenated text chunk as irrelevant,
meaning it does not contain information that can be directly used to answer the question at hand.

**G.2** **Preprocessing of Jigsaw Unintended Bias in Toxicity Classification Dataset**

We use the comments from the private leaderboard test set ( `test` ~~`p`~~ `rivate` `expanded.csv` ). The
original sample size is 97320. We reduce attention to the comments which had at least five annotators and which are at least 100 characters long. Subsequently, we group the comments into
four buckets: \[0 _,_ 0 _._ 25) _,_ \[0 _._ 25 _,_ 0 _._ 5) _,_ \[0 _._ 5 _,_ 0 _._ 75) _,_ \[0 _._ 75 _,_ 1\] based on the corresponding toxicity score, representing the fraction of annotators who marked a given comment as toxic. Finally, we select 1k
comments from each bucket at random to form the final dataset. The ground-truth label is set to
one (toxic) if and only if at least half of annotators marked the comment as toxic.

**G.3** **Prompts**

In this Section, we describe the prompt templates that were used for LLM-as-a-judge evaluations:

1. The template for relevance evaluation is provided in Figure 6.

42

Candidate Answer Label

Professor Albus Percival Wulfric Brian Dumbledore is a major character and protagonist of 0
J. K. Rowling’s Harry Potter series.

For most of the series, he is the headmaster of the wizarding school Hogwarts. 0
As part of his backstory, it is revealed that he is the founder and leader of the Order of 0
the Phoenix, an organisation dedicated to fighting the main antagonist of the series, Lord
Voldemort.

Dumbledore is portrayed by Richard Harris in the film adaptions of Harry Potter and the 0
Philosopher’s Stone and Harry Potter and the Chamber of Secrets.

After Harris’ death, Michael Gambon portrayed Dumbledore for all of the remaining flms. 1
Rowling stated she chose the name Dumbledore, which is an Early Modern English word 0
for “bumblebee”, because of Dumbledore’s love of music: she imagined him walking around
“humming to himself a lot”.

Table 4: Candidate answers for question `Q1686` : “Who plays dumbledore in harry potter 6” in
WikiQA dataset. In this example, a correct answer is present among the candidate answers,
therefore the text sample obtained by concatenation is labeled as relevant.

Candidate Answer Label

A patient with braces. 0
Dental braces (also known as orthodontic braces, or braces) are devices used in orthodontics 0
that align and straighten teeth and help to position them with regard to a person’s bite,
while also working to improve dental health.

They are often used to correct underbites, as well as malocclusions, overbites, cross bites, 0
open bites, deep bites, crooked teeth, and various other faws of the teeth and jaw.

Braces can be either cosmetic or structural. 0
Dental braces are often used in conjunction with other orthodontic appliances to help widen 0
the palate or jaws and to otherwise assist in shaping the teeth and jaws.

Table 5: Candidate answers for question `Q2943` : “What is the average wear time for braces?” in
WikiQA dataset. In this example, a correct answer is not present among the candidate answers,
therefore the text sample obtained by concatenation is labeled as irrelevant.

2. The template for toxicity evaluation is provided in Figure 7.

1. The template for summarization evaluation is provided in Figure 8.

43

Figure 6: Prompt template for evaluating text relevance. We adopt Arize [Phoenix](https://arize.com/docs/phoenix/evaluation/running-pre-tested-evals/retrieval-rag-relevance) evaluation
[template](https://arize.com/docs/phoenix/evaluation/running-pre-tested-evals/retrieval-rag-relevance) with minor changes applied to LLMaaJ response format.

44

Figure 7: Prompt template for evaluating text toxicity. We adopt Arize Phoenix [toxicity](https://arize.com/docs/phoenix/evaluation/running-pre-tested-evals/toxicity) template
with minor changes applied to LLMaaJ response format.

45

Figure 8: Prompt template for evaluating text summarization. [We adopt Arize Phoenix evaluation](https://arize.com/docs/phoenix/evaluation/running-pre-tested-evals/summarization-eval)
[template](https://arize.com/docs/phoenix/evaluation/running-pre-tested-evals/summarization-eval) with minor changes applied to LLMaaJ response format.

46
