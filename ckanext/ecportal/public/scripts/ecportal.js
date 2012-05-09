(function ($) {
    $(document).ready(function () {
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
    });
}(jQuery));
