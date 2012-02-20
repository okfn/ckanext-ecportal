(function ($) {
    $(document).ready(function () {
		/* START language selector functionality
		 * FIXME: use a local image
		 */
		$('ul.language-dd-selector').click(
			function (){
				if ($('ul.language-dd-selector li:visible').length == 1){
					// show list
					$('ul.language-dd-selector li').show();
					$('ul.language-dd-selector li img').attr('src', "http://ec.europa.eu/wel/template-2012/images/arrows-up.gif");
				} else {
					// hide list
					$('ul.language-dd-selector li:gt(0)').hide();
					$('ul.language-dd-selector li img').attr('src', "http://ec.europa.eu/wel/template-2012/images/arrows-down.gif");
				}
				})
		$('ul.language-dd-selector').mouseleave(
			function (){
				// hide list
				$('ul.language-dd-selector li:gt(0)').hide();
				$('ul.language-dd-selector li img').attr('src', "http://ec.europa.eu/wel/template-2012/images/arrows-down.gif");
				})
		/* END language selector functionality */
    });
}(jQuery));

