# Related Work

The reviewer asked that the supervisory architecture be situated against existing verifier and supervisory approaches.

Prior work includes self-critique, staged verification, separate verifier models, and multi-model review. The purpose of the comparison is architectural: to explain how information reaches the supervisor, when the supervisor forms its view, what it can observe, and how disagreement affects release.

The Dual-Lobe clinical system is organized around:
- a persistent supervisory B rather than an occasional review step;
- an independent pre-answer view of the original patient/context;
- later access to the observable A/tool execution trace and final answer;
- explicit runtime disagreement handling;
- the ability to receive additional context or information through the runtime when needed;
- patient-data handling and privacy supervision.

The manuscript should compare these properties with representative verifier/supervisor systems and cite the relevant literature. It should not turn that comparison into a separate experimental architecture or claim that verification itself is novel.
