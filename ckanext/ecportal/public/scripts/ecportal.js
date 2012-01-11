(function ($) {
  $(document).ready(function () {
    var isDatasetNew = $('body.ECPortalController.new').length > 0;
    if (isDatasetNew) {
      // Set up magic URL slug editor
      CKAN.Utils.setupUrlEditor('package');
      $('#save').val(CKAN.Strings.addDataset);
      $("#title").focus();
    }
  });
}(jQuery));

