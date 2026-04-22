"""Articles synthetiques realistes pour la generation d'un HTML de demo.

Utilise par `python -m src.main --demo` : ne necessite aucune API externe.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .models import Article


def build_demo_articles() -> list[Article]:
    """Retourne ~8 articles fictifs mais plausibles, couvrant plusieurs rubriques."""
    now = datetime.now(timezone.utc)

    demo = [
        Article(
            source="pubmed",
            source_name="PubMed",
            doi="10.2967/jnumed.2026.264000",
            pmid="40012345",
            url="https://doi.org/10.2967/jnumed.2026.264000",
            title=(
                "Long Axial Field-of-View PET/CT for Whole-Body Dosimetry of "
                "[177Lu]Lu-PSMA-617: A Prospective Single-Center Study"
            ),
            title_fr=(
                "TEP/TDM a long champ axial pour la dosimetrie corps entier "
                "du [177Lu]Lu-PSMA-617 : etude prospective monocentrique"
            ),
            abstract=(
                "We assessed whole-body dosimetry of [177Lu]Lu-PSMA-617 using a "
                "106-cm axial FOV PET/CT in 25 mCRPC patients..."
            ),
            authors=["Schmidt K", "Weber J", "Muller T", "Rossi A"],
            first_affiliation="Department of Nuclear Medicine, University Hospital Zurich, Switzerland",
            journal="J Nucl Med",
            published_at=now,
            keyword_score=6,
            relevance_score=3,
            category_id="dosimetry",
            tags=["PSMA", "Lu-177", "mCRPC", "dosimétrie", "long AFOV"],
            summary_fr={
                "context": (
                    "La dosimetrie interne en therapie PSMA reste limitee par la "
                    "duree d'acquisition et la precision des courbes temps-activite."
                ),
                "method": (
                    "25 patients mCRPC imagerie 1h, 24h, 48h, 168h post-injection "
                    "sur PET/CT 106 cm, calculs OLINDA/EXM."
                ),
                "results": (
                    "Dose moyenne glandes salivaires 0,48 Gy/GBq (+-0,12), "
                    "reins 0,62 Gy/GBq (+-0,18), moelle 0,031 Gy/GBq. "
                    "Acquisition totale reduite a 6 min."
                ),
                "implication": (
                    "Faisabilite d'une dosimetrie personnalisee en routine sans "
                    "allonger le parcours patient ; utile avant le 4e cycle."
                ),
            },
        ),
        Article(
            source="pubmed",
            source_name="PubMed",
            doi="10.1007/s00259-026-06123-4",
            pmid="40023456",
            url="https://doi.org/10.1007/s00259-026-06123-4",
            title=(
                "[68Ga]Ga-FAPI-46 PET/CT versus [18F]FDG PET/CT for Initial "
                "Staging of Pancreatic Adenocarcinoma: A Multicenter Prospective Trial"
            ),
            title_fr=(
                "[68Ga]Ga-FAPI-46 TEP/TDM versus [18F]FDG TEP/TDM pour le bilan "
                "initial des adenocarcinomes pancreatiques : essai prospectif multicentrique"
            ),
            abstract=(
                "Prospective head-to-head comparison of FAPI-46 and FDG PET/CT "
                "in 112 patients with biopsy-proven pancreatic adenocarcinoma..."
            ),
            authors=["Garcia-Lopez M", "Chen Y", "Dubois P", "Al-Ahmad R", "Becker H"],
            first_affiliation="Nuklearmedizinische Klinik, Heidelberg University Hospital",
            journal="Eur J Nucl Med Mol Imaging",
            published_at=now,
            keyword_score=5,
            relevance_score=3,
            category_id="oncology",
            tags=["FAPI", "FDG", "pancréas", "staging", "Ga-68"],
            summary_fr={
                "context": (
                    "Le FDG est limite dans l'adenocarcinome pancreatique (captation "
                    "moderee, inflammation peritumorale) ; FAPI cible le stroma."
                ),
                "method": (
                    "112 patients, TEP FAPI-46 et FDG < 7 jours d'intervalle, "
                    "lecture en aveugle, reference = chirurgie ou suivi 6 mois."
                ),
                "results": (
                    "Sensibilite primitif : FAPI 96 % vs FDG 78 % (p<0,001). "
                    "Detection de 18 % de metastases peritoneales supplementaires. "
                    "Modification de la prise en charge chez 24/112 patients (21 %)."
                ),
                "implication": (
                    "FAPI-46 devrait etre propose en complement du FDG pour le bilan "
                    "initial des adenocarcinomes pancreatiques resecables limite."
                ),
            },
        ),
        Article(
            source="pubmed",
            source_name="PubMed",
            doi="10.1016/S0140-6736(26)00456-7",
            pmid="40034567",
            url="https://doi.org/10.1016/S0140-6736(26)00456-7",
            title=(
                "[225Ac]Ac-PSMA-617 versus [177Lu]Lu-PSMA-617 in Heavily Pretreated "
                "Metastatic Castration-Resistant Prostate Cancer (ACTIVATE): "
                "A Phase 3 Randomised Trial"
            ),
            title_fr=(
                "[225Ac]Ac-PSMA-617 versus [177Lu]Lu-PSMA-617 dans le CPRCm "
                "lourdement pretraite (ACTIVATE) : essai randomise de phase 3"
            ),
            abstract=(
                "ACTIVATE randomised 412 mCRPC patients progressing after Lu-PSMA "
                "to Ac-225-PSMA vs continued Lu-PSMA..."
            ),
            authors=["Hofman M", "Emmett L", "Sandhu S", "Kratochwil C", "Morris M"],
            first_affiliation="Peter MacCallum Cancer Centre, Melbourne, Australia",
            journal="Lancet",
            published_at=now,
            keyword_score=8,
            relevance_score=3,
            category_id="theranostics",
            tags=["Ac-225", "PSMA", "mCRPC", "phase 3", "radioligand"],
            summary_fr={
                "context": (
                    "Apres progression sous Lu-PSMA, l'escalade alpha par Ac-225-PSMA "
                    "n'avait jamais ete comparee en phase 3."
                ),
                "method": (
                    "412 patients mCRPC post-Lu-PSMA, randomisation 1:1, critere "
                    "principal : survie sans progression radiologique."
                ),
                "results": (
                    "rPFS mediane 9,1 vs 4,3 mois (HR 0,48, IC 95 % 0,38-0,61). "
                    "Xerostomie grade 3+ : 14 % (Ac) vs 3 % (Lu)."
                ),
                "implication": (
                    "L'Ac-225-PSMA devient une option de reference en 2e ligne "
                    "radioligand ; peser le benefice survie contre la toxicite salivaire."
                ),
            },
        ),
        Article(
            source="rss",
            source_name="JNM RSS",
            doi="10.2967/jnumed.2026.263890",
            url="https://jnm.snmjournals.org/content/early/2026/04/21/264",
            title=(
                "Automated Amyloid PET Quantification with Deep Learning: "
                "Validation Against Centiloid in 1,200 Patients"
            ),
            title_fr=(
                "Quantification automatisee de la TEP amyloide par deep learning : "
                "validation contre le Centiloid chez 1 200 patients"
            ),
            abstract=(
                "We developed a 3D U-Net for automated SUVR and Centiloid computation "
                "from amyloid PET, trained on 800 scans and validated on 1,200..."
            ),
            authors=["Nakamura H", "Smith R", "O'Brien J"],
            first_affiliation="Department of Radiology, Kyoto University, Japan",
            journal="J Nucl Med",
            published_at=now,
            keyword_score=4,
            relevance_score=2,
            category_id="ai_radiomics",
            tags=["amyloïde", "deep learning", "Centiloid", "démence"],
            summary_fr={
                "context": (
                    "La quantification Centiloid reste manuelle ou semi-automatisee, "
                    "limitant la reproductibilite inter-centres."
                ),
                "method": (
                    "3D U-Net entraine sur 800 TEP amyloides, valide sur 1 200 "
                    "examens multi-traceurs (florbetaben, flutemetamol, florbetapir)."
                ),
                "results": (
                    "Correlation Centiloid automatique vs manuel : r=0,987. "
                    "Temps de calcul : 12 s/scan. Accord seuil 20 CL : 97 %."
                ),
                "implication": (
                    "Outil utilisable en routine pour homogeneiser la quantification "
                    "amyloide, notamment dans les indications thérapies anti-amyloide."
                ),
            },
        ),
        Article(
            source="pubmed",
            source_name="PubMed",
            doi="10.1161/CIRCULATIONAHA.126.065432",
            pmid="40045678",
            url="https://doi.org/10.1161/CIRCULATIONAHA.126.065432",
            title=(
                "99mTc-Pyrophosphate SPECT/CT in Early Wild-Type Transthyretin "
                "Cardiac Amyloidosis: Prospective Screening of 3,100 Elderly Patients"
            ),
            title_fr=(
                "TEMP/TDM au 99mTc-pyrophosphate dans l'amyloidose cardiaque "
                "ATTR-wt precoce : depistage prospectif chez 3 100 sujets ages"
            ),
            abstract=(
                "We screened 3,100 patients >75 years with unexplained heart failure "
                "using 99mTc-PYP SPECT/CT and cardiac MRI..."
            ),
            authors=["Gillmore J", "Martinez-Naharro A", "Kim J"],
            first_affiliation="National Amyloidosis Centre, University College London, UK",
            journal="Circulation",
            published_at=now,
            keyword_score=3,
            relevance_score=2,
            category_id="cardiology",
            tags=["PYP", "ATTR", "amyloïdose", "insuffisance cardiaque"],
            summary_fr={
                "context": (
                    "ATTR-wt sous-diagnostiquee chez les sujets ages avec IC a FEVG "
                    "preservee ; PYP permet le diagnostic non invasif."
                ),
                "method": (
                    "3 100 patients >75 ans, IC inexpliquee, PYP SPECT/CT + IRM. "
                    "Grade Perugini semi-quantitatif et ratio H/CL."
                ),
                "results": (
                    "Positivite grade 2-3 : 7,8 % (243/3 100). Sensibilite vs biopsie "
                    "endomyocardique : 97 %. Specificite 99 %."
                ),
                "implication": (
                    "Depistage systematique PYP justifie chez les >75 ans avec IC "
                    "inexpliquee : impact therapeutique (tafamidis) majeur."
                ),
            },
        ),
        Article(
            source="arxiv",
            source_name="arXiv (physics.med-ph)",
            arxiv_id="2604.12345",
            url="https://arxiv.org/abs/2604.12345",
            title=(
                "Denoising Low-Dose Total-Body PET with Diffusion Models: "
                "A 10x Dose Reduction Study"
            ),
            title_fr=(
                "Denoising de TEP corps entier basse dose par modeles de diffusion : "
                "etude de reduction x10 de la dose"
            ),
            abstract=(
                "We propose a conditional diffusion model for denoising 10% count "
                "total-body PET images, trained on paired full/low-count Biograph Vision..."
            ),
            authors=["Zhang W", "Kumar A", "Lindemann K"],
            first_affiliation="Stanford University, USA",
            journal="arXiv preprint",
            published_at=now,
            keyword_score=3,
            relevance_score=2,
            category_id="preprints",
            tags=["total-body PET", "diffusion models", "low-dose", "denoising"],
            summary_fr={
                "context": (
                    "Les scanners total-body permettent de diviser la dose par 10 mais "
                    "le bruit limite la lecture clinique sous 30 MBq FDG."
                ),
                "method": (
                    "Modele de diffusion conditionnel entraine sur 150 paires "
                    "full-count/10 %-count Biograph Vision Quadra, evaluation par 2 MN."
                ),
                "results": (
                    "SSIM 0,94, PSNR 41,2 dB. Detection de lesions <8 mm : 91 % vs "
                    "82 % pour EM reconstruction standard."
                ),
                "implication": (
                    "Voie prometteuse pour imager le pediatrique et les bilans de "
                    "surveillance avec des doses tres reduites."
                ),
            },
        ),
        Article(
            source="pubmed",
            source_name="PubMed",
            doi="10.1056/NEJMoa2600123",
            pmid="40056789",
            url="https://doi.org/10.1056/NEJMoa2600123",
            title=(
                "Lecanemab and Amyloid PET Visual Read Reversal in Early Alzheimer "
                "Disease: 36-Month Open-Label Extension"
            ),
            title_fr=(
                "Lecanemab et reversion de la lecture visuelle amyloide TEP dans "
                "la MA precoce : extension ouverte a 36 mois"
            ),
            abstract=(
                "36-month open-label extension of CLARITY-AD showed amyloid PET "
                "visual read conversion to negative in 68% of patients..."
            ),
            authors=["van Dyck C", "Swanson C", "Aisen P"],
            first_affiliation="Yale School of Medicine, USA",
            journal="N Engl J Med",
            published_at=now,
            keyword_score=4,
            relevance_score=3,
            category_id="neurology",
            tags=["amyloïde", "lecanemab", "Alzheimer", "F-18"],
            summary_fr={
                "context": (
                    "Apres le sweep initial, la persistance a 36 mois de la negativation "
                    "amyloide sous lecanemab etait inconnue."
                ),
                "method": (
                    "Extension ouverte CLARITY-AD, 1 280 patients, TEP amyloide "
                    "(florbetapir/florbetaben), lecture visuelle + Centiloid."
                ),
                "results": (
                    "68 % de visual read negatifs a 36 mois (vs 47 % a 18 mois). "
                    "Centiloid moyen 15 (vs 82 a l'inclusion)."
                ),
                "implication": (
                    "Argument fort pour poursuivre le traitement au-dela de 18 mois ; "
                    "la TEP amyloide devient l'indicateur cle d'arret therapeutique."
                ),
            },
        ),
        Article(
            source="pubmed",
            source_name="PubMed",
            doi="10.1148/radiol.260456",
            pmid="40067890",
            url="https://doi.org/10.1148/radiol.260456",
            title=(
                "EANM/SNMMI Procedure Guideline for [68Ga]Ga-DOTATATE PET/CT "
                "in Neuroendocrine Tumors: 2026 Update"
            ),
            title_fr=(
                "Guideline EANM/SNMMI 2026 sur la TEP/TDM au [68Ga]Ga-DOTATATE "
                "dans les tumeurs neuroendocrines : mise a jour"
            ),
            abstract=(
                "Updated joint EANM/SNMMI procedure guideline covers patient "
                "preparation, acquisition parameters, interpretation criteria..."
            ),
            authors=["Virgolini I", "Bodei L", "Hicks R", "Delbeke D"],
            first_affiliation="Department of Nuclear Medicine, Medical University of Innsbruck, Austria",
            journal="Eur J Nucl Med Mol Imaging",
            published_at=now,
            keyword_score=3,
            relevance_score=2,
            category_id="guidelines",
            tags=["DOTATATE", "TNE", "guideline", "EANM", "SNMMI"],
            summary_fr={
                "context": (
                    "La derniere guideline DOTATATE datait de 2017 ; l'avenement des "
                    "therapies Lu-DOTATATE et les nouveaux traceurs necessitaient une MAJ."
                ),
                "method": (
                    "Consensus Delphi international, 38 experts, revue systematique "
                    "2017-2025."
                ),
                "results": (
                    "Nouvelles recommandations sur : arret des analogues SST 24 h "
                    "(vs 4 semaines), SUVmax > 2x rate pour positivite, Krenning 0-4."
                ),
                "implication": (
                    "Harmonisation necessaire en pratique ; revoir le protocole "
                    "local d'arret des analogues avant imagerie."
                ),
            },
        ),
    ]

    return demo
