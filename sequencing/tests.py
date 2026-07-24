# Create your tests here.
"""
Starter test suite for the LIMS app.

Run with:
    python manage.py test sequencing

Run a single class with:
    python manage.py test sequencing.tests.CoverageCalculationTests
"""
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from .models import Individual, PacBioRun
from .forms import IndividualForm, PacBioRunForm


class CoverageCalculationTests(TestCase):
    """Tests for PacBioRun.save() coverage calc and Individual coverage properties."""

    def setUp(self):
        self.individual = Individual.objects.create(
            tolid="mTestSp1",
            species="Testus speciesus",
            expected_genome_size_bp=1_000_000_000,  # 1 Gbp
        )

    def test_coverage_calculated_on_save(self):
        run = PacBioRun.objects.create(
            individual=self.individual,
            run_id="run1",
            instrument="revio",
            total_bases=30_000_000_000,  # 30 Gbp -> 30x coverage
        )
        self.assertEqual(run.coverage, Decimal("30"))

    def test_coverage_not_calculated_without_genome_size(self):
        individual_no_size = Individual.objects.create(
            tolid="mTestSp2",
            species="Testus speciesus",
            expected_genome_size_bp=None,
        )
        run = PacBioRun.objects.create(
            individual=individual_no_size,
            run_id="run2",
            instrument="revio",
            total_bases=30_000_000_000,
        )
        self.assertIsNone(run.coverage)

    def test_coverage_not_calculated_without_total_bases(self):
        run = PacBioRun.objects.create(
            individual=self.individual,
            run_id="run3",
            instrument="revio",
        )
        self.assertIsNone(run.coverage)

    def test_total_pacbio_coverage_sums_multiple_runs(self):
        PacBioRun.objects.create(
            individual=self.individual,
            run_id="run4",
            instrument="revio",
            total_bases=10_000_000_000,  # 10x
        )
        PacBioRun.objects.create(
            individual=self.individual,
            run_id="run5",
            instrument="revio",
            total_bases=15_000_000_000,  # 15x
        )
        self.assertEqual(self.individual.total_pacbio_coverage, 25.0)

    def test_total_pacbio_coverage_none_when_no_runs(self):
        individual_no_runs = Individual.objects.create(
            tolid="mTestSp3",
            species="Testus speciesus",
            expected_genome_size_bp=1_000_000_000,
        )
        self.assertIsNone(individual_no_runs.total_pacbio_coverage)


class PacBioRunFormValidationTests(TestCase):
    """Tests for duplicate detection logic in PacBioRunForm.clean()."""

    def setUp(self):
        self.individual = Individual.objects.create(
            tolid="mTestSp1",
            species="Testus speciesus",
            expected_genome_size_bp=1_000_000_000,
        )
        self.existing_run = PacBioRun.objects.create(
            individual=self.individual,
            run_id="r84091_20260625_203158",
            metadata_id="m84091_260627_030452_s1",
            barcode="bc1017",
            instrument="revio",
        )

    def _base_form_data(self, **overrides):
        data = {
            "run_id": "r84091_20260625_203158",
            "metadata_id": "m84091_260627_030452_s1",
            "barcode": "bc1017",
            "instrument": "revio",
            "status": "planned",
        }
        data.update(overrides)
        return data

    def test_exact_duplicate_combination_is_rejected(self):
        form = PacBioRunForm(data=self._base_form_data())
        self.assertFalse(form.is_valid())
        self.assertIn("already exists", str(form.errors))

    def test_partial_match_is_not_rejected(self):
        """
        Same run_id but different metadata_id/barcode should NOT be flagged.
        This guards against the earlier bug where independent field checks
        caused false positives.
        """
        form = PacBioRunForm(data=self._base_form_data(
            metadata_id="m_different",
            barcode="bc_different",
        ))
        self.assertTrue(form.is_valid(), form.errors)

    def test_new_combination_is_accepted(self):
        form = PacBioRunForm(data=self._base_form_data(
            run_id="r_new_run",
            metadata_id="m_new",
            barcode="bc_new",
        ))
        self.assertTrue(form.is_valid(), form.errors)

    def test_blank_form_is_skipped(self):
        """An empty extra formset row shouldn't raise a duplicate error."""
        form = PacBioRunForm(data={
            "run_id": "",
            "metadata_id": "",
            "barcode": "",
            "instrument": "",
            "status": "planned",
        })
        # Should not raise the duplicate ValidationError (other required-field
        # errors may still apply depending on formset context).
        form.is_valid()
        self.assertNotIn("already exists", str(form.errors))


class IndividualFormCleaningTests(TestCase):
    """Tests for species/subspecies underscore replacement."""

    def _valid_data(self, **overrides):
        data = {
            "tolid": "mTesSpe9",
            "species": "Testus_speciesus",
            "subspecies": "",
            "tissue_type": "blood",
        }
        data.update(overrides)
        return data

    def test_underscores_replaced_in_species(self):
        form = IndividualForm(data=self._valid_data())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["species"], "Testus speciesus")

    def test_species_without_underscores_unchanged(self):
        form = IndividualForm(data=self._valid_data(species="Testus speciesus"))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["species"], "Testus speciesus")


class CheckIndividualViewTests(TestCase):
    """Tests for the check_individual AJAX endpoint."""

    def setUp(self):
        self.individual = Individual.objects.create(
            tolid="mTesSpe1",
            vglid="VGL-mTesSpe1",
            species="Testus speciesus",
        )

    def test_existing_individual_returns_data(self):
        response = self.client.get("/api/check-individual/", {"tolid": "mTesSpe1"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["exists"])
        self.assertEqual(data["species"], "Testus speciesus")

    def test_nonexistent_individual_returns_false(self):
        response = self.client.get("/api/check-individual/", {"tolid": "does_not_exist"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["exists"])

    def test_blank_tol_id_returns_false(self):
        response = self.client.get("/api/check-individual/", {"tolid": ""})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["exists"])


class SequencingEntryViewTests(TestCase):
    """Integration tests for submitting multiple PacBio runs via the formset."""

    def setUp(self):
        self.individual = Individual.objects.create(
            tolid="mTesSpe1",
            species="Testus speciesus",
            expected_genome_size_bp=1_000_000_000,
        )

    def test_submitting_two_runs_creates_two_records(self):
        data = {
            "sequencing_type": "pacbio",
            "tolid": "mTesSpe1",
            "pacbio_runs-TOTAL_FORMS": "2",
            "pacbio_runs-INITIAL_FORMS": "0",
            "pacbio_runs-MIN_NUM_FORMS": "0",
            "pacbio_runs-MAX_NUM_FORMS": "1000",
            "pacbio_runs-0-run_id": "run_a",
            "pacbio_runs-0-metadata_id": "meta_a",
            "pacbio_runs-0-barcode": "bc_a",
            "pacbio_runs-0-instrument": "revio",
            "pacbio_runs-0-status": "planned",
            "pacbio_runs-1-run_id": "run_b",
            "pacbio_runs-1-metadata_id": "meta_b",
            "pacbio_runs-1-barcode": "bc_b",
            "pacbio_runs-1-instrument": "revio",
            "pacbio_runs-1-status": "planned",
        }
        response = self.client.post("/sequencing/entry/", data)
        # Expect redirect on success
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PacBioRun.objects.filter(individual=self.individual).count(), 2)

    def test_submitting_run_for_unknown_individual_creates_nothing(self):
        data = {
            "sequencing_type": "pacbio",
            "tolid": "does_not_exist",
            "pacbio_runs-TOTAL_FORMS": "1",
            "pacbio_runs-INITIAL_FORMS": "0",
            "pacbio_runs-MIN_NUM_FORMS": "0",
            "pacbio_runs-MAX_NUM_FORMS": "1000",
            "pacbio_runs-0-run_id": "run_a",
            "pacbio_runs-0-instrument": "revio",
            "pacbio_runs-0-status": "planned",
        }
        response = self.client.post("/sequencing/entry/", data)
        self.assertEqual(PacBioRun.objects.count(), 0)


class AugmentIndividualDataTests(TestCase):
    """Tests for NCBI/GoaT lookup, with network calls mocked out."""

    @patch("sequencing.utils.get_expected_genome_size")
    @patch("sequencing.utils.get_ncbi_taxid")
    def test_augment_individual_data_combines_both_sources(self, mock_taxon, mock_genome):
        from .utils import augment_individual_data

        mock_taxon.return_value = 9796
        mock_genome.return_value = 2_500_000_000

        result = augment_individual_data("Equus caballus")

        self.assertEqual(result["taxid"], 9796)
        self.assertEqual(result["genome_size"], 2_500_000_000)
        mock_taxon.assert_called_once_with("Equus caballus")
        mock_genome.assert_called_once_with(9796)

    @patch("sequencing.utils.get_ncbi_taxid")
    def test_augment_individual_data_handles_missing_taxon(self, mock_taxon):
        from .utils import augment_individual_data

        mock_taxon.return_value = None

        result = augment_individual_data("Unknownus speciesus")

        self.assertIsNone(result["taxid"])
        self.assertIsNone(result["genome_size"])