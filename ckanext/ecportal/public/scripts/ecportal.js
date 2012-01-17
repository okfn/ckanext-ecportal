(function ($) {
    $(document).ready(function () {

        var isDatasetNew = $('body.ECPortalController.new').length > 0;
        if (isDatasetNew) {
            // Set up magic URL slug editor
            CKAN.Utils.setupUrlEditor('package');
            $('#save').val(CKAN.Strings.addDataset);
            $("#title").focus();
        }

        var isDatasetEdit = $('body.ECPortalController.edit').length > 0;
        if (isDatasetEdit) {
            CKAN.Utils.setupUrlEditor('package',readOnly=true);
            // Selectively enable the upload button
            var storageEnabled = $.inArray('storage',CKAN.plugins)>=0;
            if (storageEnabled) {
                $('li.js-upload-file').show();
            }

            // Set up hashtag nagivigation
            CKAN.Utils.setupDatasetEditNavigation();

            var _dataset = new CKAN.Model.Dataset(preload_dataset);
            var $el=$('form#dataset-edit');
            var view=new CKAN.View.DatasetEditForm({
                model: _dataset,
                el: $el
            });
            view.render();
        }

    });
}(jQuery));

