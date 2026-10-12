<?php
/**
 * Remove plugin data on uninstall. Vectors live in the API service and are not touched.
 *
 * @package VisualSearchForWooCommerce
 */

defined( 'WP_UNINSTALL_PLUGIN' ) || exit;

delete_option( 'vsw_settings' );
wp_clear_scheduled_hook( 'vsw_cleanup_uploads' );

$vsw_upload = wp_upload_dir();
$vsw_dir    = trailingslashit( $vsw_upload['basedir'] ) . 'vsw-tmp';
if ( is_dir( $vsw_dir ) ) {
	foreach ( (array) glob( $vsw_dir . '/{,.}*', GLOB_BRACE ) as $vsw_file ) {
		if ( is_file( $vsw_file ) ) {
			wp_delete_file( $vsw_file );
		}
	}
	@rmdir( $vsw_dir ); // phpcs:ignore WordPress.PHP.NoSilencedErrors
}
