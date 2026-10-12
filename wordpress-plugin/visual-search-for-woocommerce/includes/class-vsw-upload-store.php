<?php
/**
 * Short-lived storage for shopper photos.
 *
 * The photo is uploaded once (detect step) and re-used when the shopper taps
 * different detected items, so it is kept for 30 minutes behind an
 * unguessable key, in a directory that denies direct web access.
 *
 * @package VisualSearchForWooCommerce
 */

defined( 'ABSPATH' ) || exit;

class VSW_Upload_Store {

	const TTL       = 30 * MINUTE_IN_SECONDS;
	const MAX_BYTES = 10485760; // 10 MB.
	const DIR_NAME  = 'vsw-tmp';

	/** Extension => MIME. Validated against the file's real content. */
	const ALLOWED = array(
		'jpg'  => 'image/jpeg',
		'jpeg' => 'image/jpeg',
		'png'  => 'image/png',
		'webp' => 'image/webp',
	);

	public static function dir() {
		$upload = wp_upload_dir();
		return trailingslashit( $upload['basedir'] ) . self::DIR_NAME;
	}

	public static function ensure_dir() {
		$dir = self::dir();
		if ( ! wp_mkdir_p( $dir ) ) {
			return false;
		}
		if ( ! file_exists( $dir . '/.htaccess' ) ) {
			file_put_contents( $dir . '/.htaccess', "Require all denied\nDeny from all\n" ); // phpcs:ignore WordPress.WP.AlternativeFunctions
		}
		if ( ! file_exists( $dir . '/index.php' ) ) {
			file_put_contents( $dir . '/index.php', "<?php // Silence is golden.\n" ); // phpcs:ignore WordPress.WP.AlternativeFunctions
		}
		return true;
	}

	/**
	 * Validate and store an uploaded file.
	 *
	 * @param array $file Entry from $_FILES / WP_REST_Request::get_file_params().
	 * @return array|WP_Error { key, path, mime }
	 */
	public function store( $file ) {
		if ( empty( $file['tmp_name'] ) || ! isset( $file['error'] ) || UPLOAD_ERR_OK !== (int) $file['error'] || ! is_uploaded_file( $file['tmp_name'] ) ) {
			return new WP_Error( 'vsw_upload', __( 'Upload failed.', 'visual-search-for-woocommerce' ), array( 'status' => 400 ) );
		}
		if ( (int) $file['size'] > self::MAX_BYTES ) {
			return new WP_Error( 'vsw_too_large', __( 'The image is too large (max 10 MB).', 'visual-search-for-woocommerce' ), array( 'status' => 413 ) );
		}

		// Trust the bytes, not the client-supplied name or Content-Type.
		$check = wp_check_filetype_and_ext( $file['tmp_name'], sanitize_file_name( $file['name'] ?? 'upload.jpg' ), self::ALLOWED );
		$info  = @getimagesize( $file['tmp_name'] ); // phpcs:ignore WordPress.PHP.NoSilencedErrors
		$mime  = is_array( $info ) ? $info['mime'] : '';
		if ( ! in_array( $mime, self::ALLOWED, true ) || ( $check['type'] && $check['type'] !== $mime ) ) {
			return new WP_Error( 'vsw_bad_type', __( 'Please upload a JPG, PNG or WebP image.', 'visual-search-for-woocommerce' ), array( 'status' => 415 ) );
		}

		if ( ! self::ensure_dir() ) {
			return new WP_Error( 'vsw_storage', __( 'Upload failed.', 'visual-search-for-woocommerce' ), array( 'status' => 500 ) );
		}

		$key  = wp_generate_password( 32, false );
		$ext  = array_search( $mime, self::ALLOWED, true );
		$path = self::dir() . '/' . $key . '.' . $ext;
		if ( ! move_uploaded_file( $file['tmp_name'], $path ) ) {
			return new WP_Error( 'vsw_storage', __( 'Upload failed.', 'visual-search-for-woocommerce' ), array( 'status' => 500 ) );
		}

		set_transient(
			'vsw_upload_' . $key,
			array(
				'path' => $path,
				'mime' => $mime,
			),
			self::TTL
		);
		return array(
			'key'  => $key,
			'path' => $path,
			'mime' => $mime,
		);
	}

	/**
	 * @param string $key Upload key from the client.
	 * @return array|WP_Error
	 */
	public function get( $key ) {
		$key  = preg_replace( '/[^A-Za-z0-9]/', '', (string) $key );
		$data = ( 32 === strlen( $key ) ) ? get_transient( 'vsw_upload_' . $key ) : false;
		if ( ! is_array( $data ) || ! file_exists( $data['path'] ) ) {
			return new WP_Error( 'vsw_expired', __( 'Your photo expired — please upload it again.', 'visual-search-for-woocommerce' ), array( 'status' => 410 ) );
		}
		return $data;
	}

	/** Hourly cron: remove photos older than the TTL. */
	public function cleanup() {
		$files = glob( self::dir() . '/*.{jpg,png,webp}', GLOB_BRACE );
		foreach ( (array) $files as $file ) {
			if ( filemtime( $file ) < time() - self::TTL ) {
				wp_delete_file( $file );
			}
		}
	}
}
