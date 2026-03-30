from django.core.management.base import BaseCommand
from ml_engine.models import UniversityMajor, CareerPath


class Command(BaseCommand):
    help = 'Seeds the database with career paths (3 per university major)'

    def handle(self, *args, **options):
        # Clear existing career paths
        CareerPath.objects.all().delete()

        # Keys match the official_name in UniversityMajor seeding script exactly
        career_data = {
            # ===== Health =====
            "គិលានុបដ្ឋាក": [
                "គិលានុបដ្ឋាក (Nurse)",
                "គិលានុបដ្ឋាកសហគមន៍ (Community Health Nurse)",
                "អ្នកគ្រប់គ្រងថែទាំសុខភាព (Healthcare Administrator)",
            ],
            "គិលានុបដ្ឋាកបែបពាក់កណ្ដាលពេល": [
                "គិលានុបដ្ឋាក (Nurse)",
                "ជំនួយការគ្រូពេទ្យ (Medical Assistant)",
                "អ្នកថែទាំអ្នកជំងឺ (Patient Caregiver)",
            ],
            "ឆ្មបបែបពាក់កណ្ដាលពេល": [
                "ឆ្មប (Midwife)",
                "អ្នកថែទាំមាតា និងទារក (Maternal & Child Health Worker)",
                "ភ្នាក់ងារសុខភាពសហគមន៍ (Community Health Worker)",
            ],
            # ===== Finance =====
            "គណនេយ្យ និងសវនកម្ម": [
                "គណនេយ្យករ (Accountant)",
                "សវនករ (Auditor)",
                "អ្នកវិភាគហិរញ្ញវត្ថុ (Financial Analyst)",
            ],
            "គណនេយ្យ និងហិរញ្ញវត្ថុ": [
                "អ្នកវិភាគហិរញ្ញវត្ថុ (Financial Analyst)",
                "គណនេយ្យករ (Accountant)",
                "អ្នកប្រឹក្សាវិនិយោគ (Investment Advisor)",
            ],
            "ធនាគារ និងហិរញ្ញវត្ថុ": [
                "មន្ត្រីធនាគារ (Bank Officer)",
                "អ្នកវិភាគឥណទាន (Credit Analyst)",
                "អ្នកគ្រប់គ្រងហានិភ័យ (Risk Manager)",
            ],
            # ===== Hospitality =====
            "គ្រប់គ្រងសណ្ឋាគារ និងទេសចរណ៍": [
                "អ្នកគ្រប់គ្រងសណ្ឋាគារ (Hotel Manager)",
                "មគ្គុទ្ទេសក៍ទេសចរណ៍ (Tour Guide)",
                "អ្នកសម្របសម្រួលព្រឹត្តិការណ៍ (Event Coordinator)",
            ],
            # ===== Business =====
            "គ្រប់គ្រងពាណិជ្ជកម្ម (កម្មវិធីសិក្សាភាសាជាតិ)": [
                "អ្នកគ្រប់គ្រងអាជីវកម្ម (Business Manager)",
                "សហគ្រិន (Entrepreneur)",
                "អ្នកវិភាគអាជីវកម្ម (Business Analyst)",
            ],
            "គ្រប់គ្រងពាណិជ្ជកម្ម (កម្មវិធីសិក្សាអន្តរជាតិ)": [
                "អ្នកគ្រប់គ្រងអាជីវកម្មអន្តរជាតិ (International Business Manager)",
                "មន្ត្រីទំនាក់ទំនងពាណិជ្ជកម្ម (Trade Relations Officer)",
                "អ្នកវិភាគទីផ្សារ (Market Analyst)",
            ],
            # ===== Sales =====
            "ឌីជីថលម៉ាឃិធីង": [
                "អ្នកជំនាញទីផ្សារឌីជីថល (Digital Marketer)",
                "អ្នកគ្រប់គ្រងបណ្តាញសង្គម (Social Media Manager)",
                "អ្នកបង្កើតមាតិកា (Content Creator)",
            ],
            # ===== IT =====
            "ព័ត៌មានវិទ្យា": [
                "អ្នកបច្ចេកទេសព័ត៌មានវិទ្យា (IT Technician)",
                "អ្នកគ្រប់គ្រងបណ្ដាញ (Network Administrator)",
                "អ្នកគ្រប់គ្រងប្រព័ន្ធ (System Administrator)",
            ],
            "វិទ្យាសាស្រ្តកុំព្យូទ័រ": [
                "អ្នកបង្កើតកម្មវិធី (Software Developer)",
                "អ្នកវិទ្យាសាស្ត្រទិន្នន័យ (Data Scientist)",
                "វិស្វករកម្មវិធី (Software Engineer)",
            ],
            "បច្ចេកវិទ្យាប្រព័ន្ធព័ត៌មានវិទ្យានិងឌីហ្សាញ": [
                "អ្នករចនា UI/UX (UI/UX Designer)",
                "អ្នករចនាគេហទំព័រ (Web Designer)",
                "អ្នកវិភាគប្រព័ន្ធ (Systems Analyst)",
            ],
            # ===== Architecture =====
            "វិស្វកម្មសំណង់ស៊ីវិល": [
                "វិស្វករសំណង់ស៊ីវិល (Civil Engineer)",
                "អ្នកគ្រប់គ្រងគម្រោងសំណង់ (Construction Project Manager)",
                "អ្នកត្រួតពិនិត្យការដ្ឋាន (Site Supervisor)",
            ],
            "ស្ថាបត្យកម្មនិងរចនាផ្ទៃក្នុង": [
                "ស្ថាបត្យករ (Architect)",
                "អ្នករចនាផ្ទៃក្នុង (Interior Designer)",
                "អ្នករចនាលំនៅដ្ឋាន (Residential Designer)",
            ],
            "ស្ថាបត្យកម្មនិងនគរូបនីយកម្ម": [
                "ស្ថាបត្យករ (Architect)",
                "អ្នករៀបចំដែនដី (Urban Planner)",
                "អ្នកវិភាគបរិស្ថាន (Environmental Analyst)",
            ],
            # ===== Manufacturing =====
            "អគ្គិសនី និងអេឡិចត្រូនិច": [
                "វិស្វករអគ្គិសនី (Electrical Engineer)",
                "អ្នកបច្ចេកទេសអេឡិចត្រូនិច (Electronics Technician)",
                "អ្នកគ្រប់គ្រងប្រព័ន្ធបញ្ជា (Control Systems Operator)",
            ],
            # ===== Law =====
            "នីតិសាស្ត្រ": [
                "មេធាវី (Lawyer)",
                "ចៅក្រម (Judge)",
                "ព្រះរាជអាជ្ញា (Prosecutor)",
            ],
            "នីតិឯកជន": [
                "មេធាវីឯកជន (Private Lawyer)",
                "ទីប្រឹក្សាច្បាប់ក្រុមហ៊ុន (Corporate Legal Counsel)",
                "មន្ត្រីច្បាប់ (Legal Officer)",
            ],
            # ===== Government =====
            "រដ្ឋបាលសាធារណៈ": [
                "អ្នកគ្រប់គ្រងរដ្ឋបាលសាធារណៈ (Public Administrator)",
                "មន្ត្រីរាជការ (Civil Servant)",
                "អ្នកគ្រប់គ្រងគម្រោងរដ្ឋ (Government Project Manager)",
            ],
            "វិទ្យាសាស្ត្រនយោបាយ និងទំនាក់ទំនងអន្ដរជាតិ": [
                "អ្នកការទូត (Diplomat)",
                "អ្នកវិភាគនយោបាយ (Political Analyst)",
                "មន្ត្រីអង្គការអន្តរជាតិ (International Organization Officer)",
            ],
            # ===== Arts =====
            "ភាសាអង់គ្លេស": [
                "អ្នកបកប្រែ (Translator / Interpreter)",
                "គ្រូបង្រៀនភាសាអង់គ្លេស (English Teacher)",
                "មន្ត្រីទំនាក់ទំនងអន្តរជាតិ (International Communications Officer)",
            ],
            "ភាសាខ្មែរ និងបង្រៀនភាសាខ្មែរ": [
                "គ្រូបង្រៀនភាសាខ្មែរ (Khmer Language Teacher)",
                "អ្នកនិពន្ធ ឬ អ្នកសារព័ត៌មាន (Writer / Journalist)",
                "អ្នកស្រាវជ្រាវវប្បធម៌ (Cultural Researcher)",
            ],
            # ===== Education =====
            "ភាសាអង់គ្លេសសម្រាប់ការបង្រៀន": [
                "គ្រូបង្រៀនភាសាអង់គ្លេស (English Teacher)",
                "អ្នកបណ្ដុះបណ្ដាលភាសា (Language Trainer)",
                "អ្នករៀបចំកម្មវិធីសិក្សា (Curriculum Developer)",
            ],
            "បង្រៀនភាសាបារាំង": [
                "គ្រូបង្រៀនភាសាបារាំង (French Teacher)",
                "អ្នកបកប្រែភាសាបារាំង (French Translator)",
                "អ្នកសម្របសម្រួលវប្បធម៌ (Cultural Liaison)",
            ],
            "បង្រៀនភាសាកូរ៉េ": [
                "គ្រូបង្រៀនភាសាកូរ៉េ (Korean Language Teacher)",
                "អ្នកបកប្រែភាសាកូរ៉េ (Korean Interpreter)",
                "អ្នកសម្របសម្រួលវប្បធម៌កូរ៉េ (Korean Cultural Coordinator)",
            ],
            "គណិតវិទ្យា និងបង្រៀនគណិតវិទ្យា": [
                "គ្រូបង្រៀនគណិតវិទ្យា (Math Teacher)",
                "អ្នកវិភាគទិន្នន័យ (Data Analyst)",
                "អ្នកស្រាវជ្រាវវិទ្យាសាស្ត្រ (Scientific Researcher)",
            ],
            # ===== Human Services =====
            "ភាសាអង់គ្លេសសម្រាប់ទំនាក់ទំនងអន្ដរជាតិ": [
                "មន្ត្រីអង្គការក្រៅរដ្ឋាភិបាល (NGO / IO Officer)",
                "អ្នកការទូត (Diplomat)",
                "អ្នកបកប្រែផ្ទាល់មាត់ (Interpreter)",
            ],
            # ===== Agriculture =====
            "ក្សេត្រសាស្ត្រ": [
                "វិស្វករកសិកម្ម (Agricultural Engineer)",
                "អ្នកស្រាវជ្រាវដំណាំ (Crop Research Scientist)",
                "អ្នកគ្រប់គ្រងកសិដ្ឋាន (Farm Manager)",
            ],
            "កសិកម្ម និងភីវឌ្ឍន៍ជនបទ": [
                "មន្ត្រីអភិវឌ្ឍន៍ជនបទ (Rural Development Officer)",
                "មន្ត្រីផ្សព្វផ្សាយកសិកម្ម (Agricultural Extension Worker)",
                "អ្នកគ្រប់គ្រងគម្រោងអភិវឌ្ឍន៍ (Development Project Manager)",
            ],
        }

        count = 0
        not_found = []

        for official_name, jobs in career_data.items():
            try:
                major = UniversityMajor.objects.get(official_name=official_name)
                for job_title in jobs:
                    _, created = CareerPath.objects.get_or_create(
                        university_major=major,
                        job_title=job_title,
                    )
                    if created:
                        count += 1
            except UniversityMajor.DoesNotExist:
                not_found.append(official_name)

        if not_found:
            self.stdout.write(self.style.WARNING(
                f'WARNING: Could not find these majors in the database: {not_found}'
            ))

        self.stdout.write(self.style.SUCCESS(
            f'Successfully added {count} career paths to the database!'
        ))