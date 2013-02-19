(function ($) {
	$(function () {
		var arrow_url = CKAN.SITE_URL_NO_LOCALE + '/images/arrow_{0}.gif';
		var dropdown = $('#language-selector ul');
		var dropdown_image = $('#language-selector .root img');
		dropdown
			.bind('mouseleave', function() {
				_dropdown(false);
			})
			.parent()
			.bind('click', function() {
				_dropdown(true);
			});
		function _dropdown($show) {
			if ($show) {
				dropdown.show();
				dropdown_image.attr('src', arrow_url.replace('{0}', 'up'));
			} else {
				dropdown.hide();
				dropdown_image.attr('src', arrow_url.replace('{0}', 'down'));
			}
		}
	});
}(jQuery));

		/* START language selector functionality
		 */
		$('ul.language-dd-selector').click(
			function (){
				if ($('ul.language-dd-selector li:visible').length == 1){
					// show list
					$('ul.language-dd-selector li').show();
					$('ul.language-dd-selector li img').attr('src', CKAN.SITE_URL_NO_LOCALE + '/images/arrow_up.gif');
				} else {
					// hide list
					$('ul.language-dd-selector li:gt(0)').hide();
					$('ul.language-dd-selector li img').attr('src', CKAN.SITE_URL_NO_LOCALE + '/images/arrow_down.gif');
				}
				})
		$('ul.language-dd-selector').mouseleave(
			function (){
				// hide list
				$('ul.language-dd-selector li:gt(0)').hide();
								$('ul.language-dd-selector li img').attr('src', CKAN.SITE_URL_NO_LOCALE + '/images/arrow_down.gif');
				})
		/* END language selector functionality */
