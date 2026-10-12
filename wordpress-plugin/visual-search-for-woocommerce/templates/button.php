<?php
/**
 * Camera button that opens the visual search modal.
 *
 * @var string $label Accessible label.
 * @package VisualSearchForWooCommerce
 */

defined( 'ABSPATH' ) || exit;
?>
<button type="button" class="vsw-trigger" data-vsw-open aria-haspopup="dialog" aria-label="<?php echo esc_attr( $label ); ?>" title="<?php echo esc_attr( $label ); ?>">
	<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false"><path fill="currentColor" d="M9 3 7.2 5H4a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-3.2L15 3H9Zm3 5a5 5 0 1 1 0 10 5 5 0 0 1 0-10Zm0 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"/></svg>
</button>
