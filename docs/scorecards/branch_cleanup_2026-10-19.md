# 원격 브랜치 정리 기록 (2026-10-19, 평가 측, 사용자 지시)

유지: main, Steve_ACASiaLAW, evaluator/round8-promotion(열린 PR #144).
삭제 기준: (1) Steve_ACASiaLAW 또는 main에 병합된 브랜치, (2) 병합되지 않았으나 PR이 닫혀 GitHub의 refs/pull/N/head에 커밋이 보존된 브랜치. 열린 PR이 있는 브랜치는 지우지 않았다.

복구: `git push origin <SHA>:refs/heads/<브랜치>`

결과(2026-10-19, 평가 측 확인): 사용자가 삭제 명령을 실행했다. `git ls-remote --heads origin`으로 확인한 결과 원격 브랜치는 main·Steve_ACASiaLAW·evaluator/round8-promotion 3개만 남았고, 아래 목록 113개 중 남은 것은 0개다.

## (1) 병합됨

| 브랜치 | SHA |
|---|---|
| antigravity/clean-tk126-eval-phrases | 8a2dbad089cb5ef317a6180aff96720c0842f7c2 |
| antigravity/f1-review-screen | 4afb29a5af529be55c7fff90ce5583ffbd929e80 |
| antigravity/f2-review-items | 28989e1fca7f9951682cfdf1c13e7742515300ff |
| antigravity/f3-reference-review | 2e02c94c22c182daac437376cab14a4c7c3b9299 |
| antigravity/ft-temporal-review | ed8d7d1265360664abec0ecb9866699ec93a3d12 |
| antigravity/round8-privacy-boundary | aec05ffbab5e336d392be98212b754afd255ffe1 |
| antigravity/round8b-tk52 | 170c6479545133437f7ad148adfec87dfb77cd46 |
| antigravity/sanitize-train-examples-and-eval-phrases | b2febaff35945459a96acb2f9604ff499a73ca02 |
| antigravity/tk61-layout | df6571c10062169e8feb9dd3b3111367854a0613 |
| antigravity/tk63-claim-selection | 57231c2cf87ccec3b37ac56cebedffb1278e6d02 |
| antigravity/tk64-exhibit-rows | f1ba73ca27d65eaacae2340f577dfeb99e4fac09 |
| antigravity/tk65-response-envelope | a54cf40eaa08b1681fe7adbc3d61c34c16ff9889 |
| antigravity/tk66-regex-redos | 741b73985b95730a9066bbe5be2d08a8385d7202 |
| antigravity/tk67-numbering-gap-scope | 472eb69e95ec4327cedcb35374c3dbd81b0b3e32 |
| antigravity/tk68-rag-batch-truncation | 5e9f33911eb256dc27d5339e1dae91ee151228b7 |
| antigravity/tk69-ft-subitem-list | ce68dc42176e5ff88f6acc2c994c38f39156a034 |
| antigravity/tk70-rag-contradiction-promotion | db21f19d9a9ec2cc1903e236f4c08c51e786eac6 |
| antigravity/tk72-citation-extractor-linear | f18425386165e3267c3fcd9fe4f4a9905e6828ef |
| antigravity/tk74-case-table-indexing | 30f9f9280efa7d3f3e04e216a695b144e0e839a2 |
| antigravity/tk76-cycle1-phase2 | 802febfee0576ae5ce59d159e79c8b237d03092d |
| antigravity/tk76-cycle1-src-unv | 2a5dd20d827ba36f08db5ccac9fb6b1285a34823 |
| antigravity/tk76-cycle2-evi-form | ab3b1684ee635795742985564fa6a4fe6b77a47c |
| antigravity/tk76-cycle2-evi-num | 52baff95186ba2fbfc4fd12b731c6920fd922284 |
| antigravity/tk76-diagnosis | 8b91ea5583ab8d4f4fbd17176e4f4415237b5e00 |
| antigravity/tk76-evi-copy-statement-heading | ba59fbbdfb6c7c69420d4e56414988e422387c8d |
| antigravity/tk76-evi-date-context | 78fc3df5b627dab7d1e9dbcd72a2007bff3a98d3 |
| antigravity/tk77-timing-test-gc-flake | 01593e3ad9c25aaf8c3cc32ff3c8046592894045 |
| antigravity/tk79-render-secret-group | c6c9480baa48c0d29a33ed905477c8ba725d4d96 |
| antigravity/tk81-evi-form-exclusion-overreach | 882400841640236f1913112ebe67f6cd88a6a14f |
| antigravity/upload-privacy-notice | 41faa2e9d645e8cc77629a97b9b6c94e945911f8 |
| antigravity/version-0.11.0 | 687da7a41d52bc1961211d18d5eade9b2a05eede |
| antigravity/version-0.12.0 | 871520f9cbf64387acda6ea8668e052d5ad1da4e |
| antigravity/version-0.13.1 | 244609bf5f1930bb9b99632f7f019ba397c21bb3 |
| ccr-7be8351f-nx7h86 | 9dd2312e729f2bf97b50af813db1d66963ff01f3 |
| claude/codeql-steve-pr-gate | 05e540919eee927b931ddfbe713fea6baebef43d |
| claude/online-measurement-setup-wotm23 | a51b1d5f52f5c84242c8b5fc8aa3408e6e7dfba0 |
| codex/10h-tk55-input-contracts | ce833558f184725bf0b0c6f49c393fba6023c94c |
| codex/10h-track-a | c6e5437a1280fcf10f07a84be8e47edc7edd43a0 |
| codex/10h-track-a-unknown | ebd6b51a7e3e164793c21111b3b0542fb133a927 |
| codex/10h-track-b | 0261ea05d73cce28292983f17b686b6db3cef909 |
| codex/10h-version-only | a4b0688a36f1c1f1a0e8dc8b13c01dd97ab26964 |
| codex/codeql-purge-log | 1707f5949561c4c4b75bbab408254d82cec7255d |
| codex/efficient-legal-review | c35bb2a5d2e3ce777a61929a822c8117914a3acb |
| codex/korean-law-review-profile | 3805e9495985626224c8c28ab06811a8068fb034 |
| codex/post013-tk55-excerpts | 2f4e798a052ef2bd6b581d7e69c3738aa1c79eb2 |
| codex/post013-track-a | b1e506f2eab2b830cb8fb7fd074d22dcdc3be589 |
| codex/post013-track-a-named-actualtext | 5e6e85932a5579eedb84b7bc9ba8f75ec3c7d25d |
| codex/post013-track-b | 86e75e34c213548c307e71b273b3933f3614bfec |
| codex/round8c-key-context | aec05ffbab5e336d392be98212b754afd255ffe1 |
| codex/stability-recovery | 61ef12f82c6d8c75f703809a7fc88051b6147fe9 |
| codex/tk24-statutory-period-exclusion | 0ad4fac3fe1b8c23514dc607939464698dbe46b7 |
| codex/tk43-name-overmasking-resume | e4867e70ace29e2afbf4fa8bdfdde4726a8c570f |
| codex/tk44-form-inspection-product | 3f9aef22c8987c6d954f980c461a83245322518b |
| codex/tk55-generated-claim-identifiers | 2936764c335386a4140c773354dfd8b3e7f8f089 |
| codex/tk56-structured-name-boundary | 71905ebeaccd1985ccb813158b94591f49f7d22e |
| codex/tk58-account-kind | f2033e192c4e3bac179367b7c904b93bf5cc96b9 |
| codex/tk71-structured-case-table | 7aecc5162b39af88b9f228baa4710c4f65a99d65 |
| codex/tk73-numbering-product | 9a56188f23857ff04355bfd71649c94d95e6eb0c |
| codex/tk78-opt-in-routing | 58ca27212aabfa2f89257806db5f58890aa2d1ac |
| codex/version-0.10.0 | 472861e1d0730403330e2ede78812312d3fa50e4 |
| evaluator/0.13-deployment-record | 199dffd4cabfb2dd1875515fc8aeaacbd9235eac |
| evaluator/10h-release-integration | a4b0688a36f1c1f1a0e8dc8b13c01dd97ab26964 |
| evaluator/20261016-targets-checklist | 207d56460689227bb34980f28c20eca8c430fb9f |
| evaluator/codeql-protected-paths | e779a3fc28c781a1dabd288154fcb06f0d3f9b26 |
| evaluator/codex-remaining-review-20261017 | 8104736dbb439c27e8642bc48cd3e50acacd5276 |
| evaluator/fixed-bench-v2-prompt-20261017 | e17916e295b11ec9d438a0150eb338ab9712e44c |
| evaluator/fixed-benchmark-metrics | ea5cbc59cfb305e6a403cd05d2bd6c85ea463bb2 |
| evaluator/kr-legal-briefs-reference-20261010 | 7cba973d324ccfaaa4d83ff2ea82a34c083d7d2c |
| evaluator/next-for-codex-cleanup-20261017 | 36a639abb102bd1c29c3a4adfe983447b2fd554e |
| evaluator/post013-accepted | 070238666686ac734c92d3bb26d1bbd96702634e |
| evaluator/post013-deployment-record | 2c06a37214516e3a42cf8b613a0ba8666a0980fe |
| evaluator/post013-online-review | df2616eec996424bf544141efe7333f623807f18 |
| evaluator/post013-release-record | 525a0b50d2cd2418a00d97756c7f6f2c6f2be3cf |
| evaluator/post013-remaining | 90ef392e61b3398f67647a7c9a93b0b6b00ede27 |
| evaluator/release-readiness-final | 4ec85a8df1b4d30071ac2461bfdd1febe612339f |
| evaluator/role-switch-antigravity-claude | c514eed5cc51672b007ae3ec9d2e4136f8e6ed3a |
| evaluator/round7-closure-record | 5d3cee58464b8e208e66f5a96591eee9fdac8231 |
| evaluator/round8-decisions | f8dbdc2b8228e3d89bd46b517b0c3f639cfcbcba |
| evaluator/round8-privacy-prep | 1b16e21794221d6b87b6f91ba7d7118f6d5bf003 |
| evaluator/round8-verdict | c754f069df8fa61d2baff076b471c336125cefca |
| evaluator/round8b-prompt | aef651c233604cb8995e8b9bbf01eec9f5aa1458 |
| evaluator/round8b-verdict | c9b5bf03239e963059305521c8dc34c669663a84 |
| evaluator/round8b-verdict-2 | c9b5bf03239e963059305521c8dc34c669663a84 |
| evaluator/tk76-memo-verdict-20261017 | a2475e73d31b0c94185f9a94add75ea4eb788fde |
| evaluator/tk76-pr114-verdict | 003cb70f06925d3f1f23908c40366dcc2cc8993d |
| super_cosmos_surges_19h47 | 4da3910193ba726a61938e6a45c2f379fb30e906 |

## (2) 미병합·PR 닫힘 (PR head로 보존)

| 브랜치 | SHA | 보존 PR head |
|---|---|---|
| codex/10h-claude-price | 50017427cece319c8368761ce19ce31d67b4335c | #87(5001742) |
| codex/10h-track-a-tk45 | e21c40d442f521782cd7d85a18b8fb40655b403d | #84(e21c40d) |
| codex/10h-track-a-tk45-auxiliary-design | f51abebe31395a2b2d0faa3371f854785db797a6 | #84(e21c40d) |
| codex/10h-track-a-tk45-auxiliary-implementation | e21c40d442f521782cd7d85a18b8fb40655b403d | #84(e21c40d) |
| codex/10h-track-a-tk45-case-adnominal-design | bb68a0092c7d1e674e74350288575ae9a5e252f9 | #84(e21c40d) |
| codex/10h-track-a-tk45-case-adnominal-implementation | 258907052d538192187cf4356338715e648b27fb | #84(e21c40d) |
| codex/10h-track-a-tk45-clause-effect-design | f929dc893e12f8d21f330e0b03409757e46c2117 | #84(e21c40d) |
| codex/10h-track-a-tk45-context-design | 1c8ebe8204b4861ded1f03ae776a63c94e877936 | #84(e21c40d) |
| codex/10h-track-a-tk45-context-proof | 0c09885a557d879f50d21870111a27426bee9db3 | #84(e21c40d) |
| codex/10h-track-a-tk45-context-proof-design | 5203f9042d83dce989ac0989313e621e1fc29453 | #84(e21c40d) |
| codex/10h-track-a-tk45-context-proposition | 441249b01d14c6ecee6231a95cb9d8bece222f68 | #84(e21c40d) |
| codex/10h-track-a-tk45-context-proposition-design | ea80ae3c91aacb915a79f970d2415aac8eb6e70e | #84(e21c40d) |
| codex/10h-track-a-tk45-context-resolution | 32a1aafd57b792c048cea540968f776d0460f9dc | #84(e21c40d) |
| codex/10h-track-a-tk45-extent-design | c70b2dec9b409f2823e226d758a01eb06bda5c7c | #84(e21c40d) |
| codex/10h-track-a-tk45-reference-condition-design | 5c5841a3aeb6dfa7cdb0845c8d5d7d7020c37dc2 | #84(e21c40d) |
| codex/10h-track-a-tk45-reference-condition-guard | bcea17c660f9cbd3055952b2ae0f1b26f2cfda49 | #84(e21c40d) |
| codex/10h-track-a-tk45-typed-effect | 1a324c922a81e7481ca31b6a415829821fba2447 | #84(e21c40d) |
| codex/10h-track-c | 214334ddb916a0a856e7a4a55d39cbd180c5ec1a | #79(214334d) |
| codex/post013-track-a-tk45-applicability | 5c69062234b5efce9cc6def082cef9f34ba19319 | #96(5c69062) |
| codex/post013-track-a-tk45-design | 9ebd28735949b8c5d4a7080b527b9444d0c0980a | #93(9ebd287) |
| codex/post013-track-c | 401d0988e0440a8db49b6e1c9f505b26d4fd587c | #92(401d098) |
| codex/tk44-form-inspection-design | 86b7fa562f73c9396c79cd0b31b95814df20808a | #108(86b7fa5) |
| codex/tk44-tk49-layout-signal-design | e20bd6c13ad8cecc23cd46b8061cfa7221ca34db | #63(e20bd6c) |
| codex/tk55-tk57-design | 0db0bede944967b9c74954cdb0719f6d125bef12 | #80(0db0bed) |
| codex/tk73-document-provenance | b533922f3e584719785f7a14a5048050dbf7650b | #85(b533922) |
| codex/tk73-minimal-key-audit | 59b62fcfcafba53da0e07ff85f2437805b97acb2 | #117(59b62fc) |
| evaluator/pr128-acceptance-20261018 | 1924c4da062ea2b4e8f9e02d40ceb6e0e6ad8e23 | #129(1924c4d) |
