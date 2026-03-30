# សេចក្តីពិពណ៌នាបែបនិក្ខេបបទអំពីតួនាទីរបស់ TabNet នៅក្នុង Backend

## សេចក្តីសង្ខេប

នៅក្នុងគម្រោងនេះ TabNet មិនត្រឹមតែជាម៉ូឌែល Machine Learning សម្រាប់ទស្សន៍ទាយមុខជំនាញប៉ុណ្ណោះទេ ប៉ុន្តែវាជាស្នូលនៃប្រព័ន្ធសម្រេចចិត្តទាំងមូលនៅក្នុង `backend/ml_engine` ផងដែរ។ Backend បានប្រើ TabNet ដើម្បីបម្លែងពិន្ទុសំណួរស្ទង់មតិរបស់សិស្សចំនួន 256 មុខងារ ទៅជាការព្យាករណ៍មុខជំនាញដែលសមស្រប បង្ហាញលទ្ធផលជាប្រូបាប៊ីលីតេ គ្រប់គ្រងការបណ្តុះបណ្តាលម៉ូឌែលឡើងវិញ រក្សាទុក version នៃម៉ូឌែល និងបង្កើតការពន្យល់សម្រាប់លទ្ធផលផងដែរ។ ដូច្នេះ TabNet នៅទីនេះមានតួនាទីជា predictive engine, training engine, explainability source និងជាគ្រឿងមូលដ្ឋានសម្រាប់ adaptive recommendation។

## ១. បរិបទនៃប្រព័ន្ធ

គោលបំណងសំខាន់របស់ backend នេះគឺបម្រើការណ៍ណែនាំមុខជំនាញដល់សិស្ស ដោយផ្អែកលើចម្លើយសំណួរ NEA ដែលត្រូវបានបំបែកជាពីរផ្នែកធំៗ៖

- `ch1` ជាសំណួរអំពីចំណាប់អារម្មណ៍
- `ch2` ជាសំណួរអំពីជំនាញ

ទិន្នន័យទាំងពីរនេះត្រូវបាន flatten ទៅជាវ៉ិចទ័រមានប្រវែង `256` តាមរយៈ `backend/ml_engine/services/data_processor.py`។ វ៉ិចទ័រនេះគឺជាអ៊ីនផុតផ្ទាល់របស់ TabNet។ ដូច្នេះ នៅក្នុងស្ថាបត្យកម្មនេះ TabNet ទទួលខុសត្រូវក្នុងការសិក្សាទម្រង់ទំនាក់ទំនងស្មុគស្មាញរវាងចំណាប់អារម្មណ៍ ជំនាញ និងមុខជំនាញគោលដៅ។

## ២. តួនាទីស្នូលរបស់ TabNet

### ២.១ តួនាទីជាម៉ូឌែលទស្សន៍ទាយ

នៅក្នុង `backend/ml_engine/services/recommender.py` ប្រព័ន្ធប្រើ `TabNetClassifier` ដើម្បីផ្ទុកម៉ូឌែលដែលបានបណ្តុះបណ្តាលរួចពី `saved_models/major_model.zip`។ នៅពេល frontend ឬ client ផ្ញើចម្លើយសិស្សមកកាន់ API `predict/` នោះ backend នឹង:

1. បម្លែង JSON ទៅជា array 256 ធាតុ
2. ផ្ញើ array នោះចូល TabNet
3. ទទួល class prediction ត្រឡប់មកវិញ
4. បកប្រែ class index ទៅជាឈ្មោះមុខជំនាញពិត

មានន័យថា TabNet គឺជាអង្គធាតុសម្រេចថា “សិស្សនេះគួរត្រូវបានណែនាំទៅមុខជំនាញអ្វី”។

### ២.២ តួនាទីជាម៉ាស៊ីនបណ្តុះបណ្តាល

នៅក្នុង `backend/ml_engine/services/tabnet_trainer.py` TabNet ត្រូវបានប្រើឡើងវិញសម្រាប់ retraining។ ដំណើរការនេះរួមមាន៖

- បង្កើត synthetic data តាម `synthetic_gen.py`
- ផ្ទុក real data ពី CSV តាម `data_processor.py`
- បញ្ចូល synthetic និង real data ចូលគ្នា
- បំបែកជា training set និង validation set
- បណ្តុះបណ្តាល `TabNetClassifier.fit(...)`
- គណនាម៉ែត្រវាស់ប្រសិទ្ធភាព
- រក្សាទុកម៉ូឌែលថ្មីជារៀងរាល់ version
- កំណត់ម៉ូឌែលថ្មីជាម៉ូឌែល active

ដូច្នេះ TabNet មិនមែនគ្រាន់តែសម្រាប់ inference ទេ ប៉ុន្តែវាជាគ្រឿងស្នូលនៃ lifecycle របស់ម៉ូឌែលទាំងមូល។

### ២.៣ តួនាទីផ្នែក Explainability

នៅក្នុង `backend/ml_engine/services/adaptive_recommender.py` ប្រព័ន្ធប្រើ `model.explain(...)` របស់ TabNet ដើម្បីទាញ feature importance សម្រាប់ prediction មួយៗ។ នេះអនុញ្ញាតឱ្យ backend អាចបង្ហាញថា សំណួរណាខ្លះដែលមានឥទ្ធិពលខ្លាំងជាងគេក្នុងការផ្តល់អនុសាសន៍មុខជំនាញ។ ចំណុចនេះមានសារៈសំខាន់ខ្លាំងក្នុងបរិបទអប់រំ ព្រោះអ្នកប្រើមិនត្រូវការតែលទ្ធផលប៉ុណ្ណោះទេ ប៉ុន្តែត្រូវការហេតុផលនៃលទ្ធផលផងដែរ។

## ៣. ស្ថាបត្យកម្មការងាររបស់ TabNet នៅក្នុង Backend

### ៣.១ ស្រទាប់ទិន្នន័យ

ស្រទាប់ទិន្នន័យមានមុខងាររៀបចំអ៊ីនផុតឱ្យសមស្របសម្រាប់ TabNet៖

- `parse_json_to_flat_array()` បម្លែង JSON ទៅជា feature vector 256
- `load_all_real_data()` អាន CSV ពិត និងបង្កើត `X_real`, `y_real`, `weights_real`
- `get_major_id()` បម្លែងឈ្មោះមុខជំនាញទៅជា major ID

លក្ខណៈពិសេសមួយគឺ real data អាចមាន `User_Rating` ដើម្បីបម្លែងទៅជា sample weight។ នេះមានន័យថា TabNet នៅពេល train មិនមើលគ្រប់ sample ស្មើគ្នាទេ ប៉ុន្តែអាចឱ្យទិន្នន័យដែលមានតម្លៃខ្ពស់ជាង មានឥទ្ធិពលខ្លាំងជាងក្នុងការរៀន។

### ៣.២ ស្រទាប់បង្កើតទិន្នន័យសិប្បនិម្មិត

`backend/ml_engine/services/synthetic_gen.py` បង្កើត synthetic student profiles ដើម្បីបន្ថែមទិន្នន័យ train។ វាមិនបង្កើតទិន្នន័យចៃដន្យទាំងស្រុងទេ ប៉ុន្តែបង្កើតតាម logic ដូចជា៖

- primary major
- secondary major
- major correlations
- interest-skill correlation
- personality bias
- gender bias
- realistic noise

អត្ថន័យរបស់វាគឺ TabNet ត្រូវបានគាំទ្រដោយ data augmentation ដើម្បីអាចរៀន pattern បានច្រើនជាងការពឹងផ្អែកលើ CSV ពិតតែប៉ុណ្ណោះ។

### ៣.៣ ស្រទាប់ Training Orchestration

`train_hybrid_model_task()` គឺជាបេះដូងនៃ retraining pipeline។ មុខងារនេះធ្វើការងារសំខាន់ៗដូចខាងក្រោម៖

1. កំណត់ major ដែលត្រូវបណ្តុះបណ្តាល
2. បង្កើត synthetic data ប្រសិនបើត្រូវការ
3. ផ្ទុក real data
4. បញ្ចូលទិន្នន័យទាំងពីរចូលគ្នា
5. split training/validation
6. train `TabNetClassifier`
7. កត់ត្រា logs និង progress
8. evaluate performance
9. save model version
10. reload model សម្រាប់ inference ភ្លាមៗ

ការចាប់ផ្តើម training ត្រូវបានធ្វើក្នុង background thread តាម `start_training()` ដូច្នេះ Django web process មិនត្រូវបាន block។

### ៣.៤ ស្រទាប់ Monitoring

`TrainingState` រក្សាទុកស្ថានភាព training ក្នុង `training_state.json`។ វាមានតួនាទី:

- កត់ត្រា status ដូចជា `IDLE`, `TRAINING`, `STOPPING`, `COMPLETED`, `ERROR`
- កត់ត្រា epoch progress
- កត់ត្រា logs សម្រាប់ UI
- កត់ត្រា metrics

ចំណុចនេះបង្ហាញថា TabNet ត្រូវបានដាក់បញ្ចូលក្នុងប្រព័ន្ធគ្រប់គ្រងប្រតិបត្តិការមួយពេញលេញ មិនមែនជាកូដសាកល្បង ML ធម្មតាទេ។

## ៤. លំហូរទិន្នន័យពីអ្នកប្រើរហូតដល់ការណែនាំ

លំហូរការងាររបស់ TabNet អាចពិពណ៌នាបានដូចខាងក្រោម៖

1. អ្នកប្រើឆ្លើយសំណួរ interest និង skill
2. Backend ទទួល JSON តាម `RecommendationAPI`
3. `data_processor.py` បម្លែងចម្លើយទៅជា array 256
4. `MajorRecommender` ផ្ទុក TabNet model
5. TabNet prediction ត្រូវបានអនុវត្ត
6. Backend បម្លែង class index ទៅឈ្មោះ major
7. API ត្រឡប់លទ្ធផលទៅ frontend

ក្នុងករណី adaptive mode លំហូរនេះកាន់តែជ្រៅជាងមុន ព្រោះ backend មិនត្រឹមតែសុំលទ្ធផលទេ ប៉ុន្តែសុំព្រូបាប៊ីលីតេ ស្ទង់មើល uncertainty និងកំណត់សំណួរបន្ទាប់ដែលគួរតែសួរ។

## ៥. TabNet ក្នុង Adaptive Recommendation

ផ្នែក `AdaptiveRecommender` បង្ហាញថា TabNet ត្រូវបានប្រើលើសពីការទស្សន៍ទាយចុងក្រោយ។ វាក្លាយជាគ្រឿងបញ្ជារសម្រាប់ adaptive survey ផងដែរ។

### ៥.១ Prediction ជាមួយទិន្នន័យមិនទាន់ពេញ

នៅពេលសិស្សមិនទាន់ឆ្លើយគ្រប់ 256 សំណួរ backend បំពេញតម្លៃដែលមិនទាន់ឆ្លើយជាសូន្យ រួចហៅ `predict_proba()`។ វាអនុញ្ញាតឱ្យ TabNet ប៉ាន់ស្មានលទ្ធផលបណ្តោះអាសន្ន និងបង្ហាញ៖

- major ដែលមានឱកាសខ្ពស់បំផុត
- confidence
- top 3 majors
- uncertainty

### ៥.២ ការជ្រើសសំណួរបន្ទាប់

ប្រព័ន្ធ adaptive មិនទាន់យក question importance ពី TabNet ដោយផ្ទាល់សម្រាប់គ្រប់ជំហានទេ។ វាប្រើ heuristic weights ជាមូលដ្ឋានសម្រាប់រៀបអាទិភាពសំណួរ បន្ទាប់មកបូកបន្ថែមដោយផ្អែកលើ major ដែលកំពុងមានប្រូបាប៊ីលីតេខ្ពស់។ នេះមានន័យថា TabNet ជាអ្នកផ្តល់ probability signal ខណៈ logic ជ្រើសសំណួរបន្ទាប់នៅតែជាការរួមបញ្ចូលរវាង ML និង rule-based strategy។

### ៥.៣ Explainable AI

ចំណុចខ្លាំងមួយគឺ adaptive mode អាចប្រើ `model.explain()` ដើម្បីរក top features ដែលជះឥទ្ធិពលខ្លាំងលើការសម្រេចចិត្ត។ Backend បន្ទាប់មកបម្លែង feature index ទៅសំណួរពិតតាម `question_mapper.py` ដូច្នេះលទ្ធផលដែលបានបង្ហាញអាចនិយាយជាភាសាមនុស្សបានថា “សំណួរអំពីចំណាប់អារម្មណ៍ ឬជំនាញណាខ្លះ បានជំរុញឱ្យប្រព័ន្ធណែនាំ major នេះ”។

## ៦. TabNet ក្នុង Admin និង Model Management

TabNet ត្រូវបានភ្ជាប់ជាមួយ admin workflow ដោយផ្ទាល់។

### ៦.១ Retrain Interface

នៅ `backend/ml_engine/views.py` និង `templates/ml_engine/retrain.html` អ្នកគ្រប់គ្រងអាច:

- upload CSV dataset
- កំណត់ synthetic sample count
- កំណត់ `max_epochs`
- កំណត់ `patience`
- កំណត់ `batch_size`
- ជ្រើស major ដែលត្រូវ train

នេះបង្ហាញថា TabNet ត្រូវបានដាក់ឱ្យប្រើក្នុងលក្ខណៈ operational system ដែលអាច retrain បានពី UI មិនចាំបាច់កែ code ដោយដៃ។

### ៦.២ Versioning និង Activation

នៅ `model_manager.py` ម៉ូឌែលថ្មីត្រូវបានរក្សាទុកជាឈ្មោះ timestamped model ហើយ metadata ត្រូវបានកត់ត្រាទុកក្នុង `models_metadata.json`។ បន្ទាប់មក file នោះត្រូវបាន copy ទៅ `major_model.zip` ដើម្បីក្លាយជាម៉ូឌែល active។

ដំណើរការនេះធ្វើឱ្យ TabNet មានលក្ខណៈ:

- version control សម្រាប់ម៉ូឌែល
- rollback/activate model ផ្សេងបាន
- traceability នៃ metrics និង config

### ៦.៣ Major Configuration

`major_config.py` រក្សាទុក major ដែលត្រូវបានអនុញ្ញាតឱ្យ train។ ពេល train តែ major មួយចំនួន backend នឹង remap label ទៅជា class index ថ្មី ហើយ `MajorRecommender` នឹង map ត្រឡប់ពី class index ទៅ original major ID នៅពេល inference។ នេះមានន័យថា TabNet ក្នុងប្រព័ន្ធនេះអាចធ្វើការជាមួយ label space ដែលអាចបត់បែនបាន មិនចាំបាច់តែងតែ train លើ major ទាំង 16 ទេ។

## ៧. លទ្ធផលវាយតម្លៃដែលរក្សាទុកក្នុងប្រព័ន្ធ

យោងតាម snapshot ដែលមានក្នុង `saved_models/training_state.json` និង `saved_models/major_config.json` នៅថ្ងៃទី 25 ខែមីនា ឆ្នាំ 2026 ប្រព័ន្ធបានបណ្តុះបណ្តាល TabNet លើ major ចំនួន 14។ Logs បង្ហាញថា៖

- ប្រើ synthetic data ចំនួន `10000` samples
- ប្រើ real data ចំនួន `9` samples
- បណ្តុះបណ្តាលរហូតដល់ epoch ទី `17` ពី `20`
- early stopping ត្រូវបានអនុវត្ត
- best validation accuracy ប្រហែល `85.51%`
- top-3 accuracy ប្រហែល `91.11%`

ទិន្នន័យនេះបង្ហាញថា TabNet នៅក្នុង backend មិនត្រឹមតែមានការរចនាផ្នែកស្ថាបត្យកម្មល្អប៉ុណ្ណោះទេ ប៉ុន្តែថែមទាំងមានការវាស់វែងប្រសិទ្ធភាពជាក់ស្តែងផងដែរ។

## ៨. គុណសម្បត្តិនៃការប្រើ TabNet នៅក្នុងគម្រោងនេះ

ការជ្រើស TabNet សមស្របសម្រាប់ backend នេះដោយសារហេតុផលសំខាន់ៗ៖

- វាសមស្របសម្រាប់ tabular data ដែលជាប្រភេទទិន្នន័យស្ទង់មតិ
- អាចរៀន non-linear relationships រវាងសំណួរច្រើនមុខ
- គាំទ្រ `predict_proba()` ដែលល្អសម្រាប់ adaptive flow
- គាំទ្រ `explain()` ដែលមានប្រយោជន៍សម្រាប់ XAI
- អាចបណ្តុះបណ្តាលជាមួយ sample weights
- អាចប្រើ early stopping និង validation monitoring បានងាយ

បើប្រៀបធៀបនឹងវិធីបូកពិន្ទុធម្មតា TabNet អាចស្គាល់ pattern ឆ្លងកាត់ប្រភេទសំណួរ និងទាញយកសញ្ញាដែលលាក់ខ្លួននៅក្នុងទិន្នន័យបានល្អជាង។

## ៩. កម្រិតកំណត់ និងចំណុចដែលគួរពិចារណា

ទោះបី TabNet មានសារៈសំខាន់ខ្លាំងក៏ដោយ កូដបច្ចុប្បន្ននៅ backend ក៏បង្ហាញកម្រិតកំណត់មួយចំនួនដែរ៖

- real data នៅមានចំនួនតិច ហើយការបណ្តុះបណ្តាលពឹងលើ synthetic data ខ្លាំង
- adaptive question importance នៅមិនទាន់យកពី model importance ដោយផ្ទាល់ទាំងស្រុង
- unanswered questions ត្រូវបានបំពេញជាសូន្យ ដែលអាចបង្ក bias ខ្លះ
- gender bias និង personality bias ក្នុង synthetic generator ត្រូវការពិនិត្យផ្នែកសីលធម៌ និង fairness
- performance ល្អក្នុង logs មិនមានន័យថា generalization ល្អសម្រាប់ទិន្នន័យពិតគ្រប់បរិបទទាំងអស់ទេ

ដូច្នេះ TabNet ជាឧបករណ៍សំខាន់ ប៉ុន្តែគុណភាពចុងក្រោយរបស់ប្រព័ន្ធនៅតែអាស្រ័យលើគុណភាព data engineering និង evaluation strategy ផងដែរ។

## សេចក្តីសន្និដ្ឋាន

អាចសន្និដ្ឋានបានថា TabNet នៅក្នុង backend នេះមានតួនាទីធំលើសពី “ម៉ូឌែលមួយ” ធម្មតា។ វាជាគ្រឹះនៃប្រព័ន្ធណែនាំមុខជំនាញទាំងមូល ដោយពាក់ព័ន្ធចាប់ពីការបម្លែងទិន្នន័យ ការបណ្តុះបណ្តាល ការទស្សន៍ទាយ ការពន្យល់លទ្ធផល ការគ្រប់គ្រង version និង adaptive questioning។ ក្នុងន័យបែបនិក្ខេបបទ អាចនិយាយបានថា TabNet គឺជាម៉ាស៊ីនចម្បងដែលបម្លែងទិន្នន័យស្ទង់មតិរបស់សិស្សទៅជាចំណេះដឹងសម្រេចចិត្ត ដែលអាចប្រើប្រាស់បានក្នុងប្រព័ន្ធណែនាំអាជីព និងមុខជំនាញឆ្លាតវៃ។

## ឯកសារកូដដែលពាក់ព័ន្ធ

- `backend/ml_engine/services/recommender.py`
- `backend/ml_engine/services/tabnet_trainer.py`
- `backend/ml_engine/services/adaptive_recommender.py`
- `backend/ml_engine/services/data_processor.py`
- `backend/ml_engine/services/synthetic_gen.py`
- `backend/ml_engine/services/model_manager.py`
- `backend/ml_engine/services/major_config.py`
- `backend/ml_engine/services/question_mapper.py`
- `backend/ml_engine/views.py`
- `backend/ml_engine/urls.py`
- `backend/ml_engine/urls_pages.py`
