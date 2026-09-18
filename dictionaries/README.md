# Dictionaries

## `green_dictionary_ilo_2025.csv`
Transcribed from Table A.1 of Delaporte, I., Escudero, V. and Adamczyk, W. (2025), *Measuring the Greenness of
Jobs in Emerging Economies: A Big Data Text Analysis Approach*, ILO Research Brief, Geneva
(https://doi.org/10.54394/JKGV7887, licensed CC BY 4.0). 535 entries across the nine sustainability domains
G01–G09. The brief reports "472 keywords"; the difference reflects how multi-word expressions and near-variants are
counted in the published table. Nothing was added or removed; one duplicate ("hazardous waste", listed under G04
and G05) is kept in both domains as published.

## `skills_taxonomy_ilo_2025.csv`
Transcribed from Table A.1 of Adamczyk, W., Boehmer, S., Delaporte, I., Escudero, V. and Liepmann, H. (2025),
*Developing a New Method to Uncover Skills Trends in Emerging Economies Using Online Data and NLP Techniques*,
ILO Research Brief, Geneva (https://doi.org/10.54394/HQQX3200). The table lists the *selected* keywords of the
15 subcategories, not the full dictionary (the Uruguayan version has 669 expressions with synonyms), so skills
variables built here are a partial replication and are labelled as such in all outputs.
Editorial decisions when transcribing: "math(ematics)" expanded to "math" and "mathematics"; "(un)supervised
learning" to both forms; "natural language processing (NLP)" to both forms; "computer vision decision trees"
split at the missing comma; "cost Softland" and "patient advertise" split likewise; "Cloudboooks" corrected to
"cloudbooks". British and American spellings of "modelling"/"visualisation" both included.

## `exceptions_en_us.csv`
Country- and corpus-specific exception rules (terms excluded or contexts excluded) created during validation.
Every row states the reason and the evidence. This is the only file that is meant to change from one country
application to the next.

## `linkedin_industry_to_isic_section.csv`
Manual mapping of the 422 LinkedIn industry labels to ISIC Rev. 4 sections (A–U). LinkedIn industries are not an
official classification; the mapping is a documented simplification for this demonstration.
