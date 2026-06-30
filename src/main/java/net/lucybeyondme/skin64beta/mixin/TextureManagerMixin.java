package net.lucybeyondme.skin64beta.mixin;

import net.minecraft.client.texture.TextureManager;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

import javax.imageio.ImageIO;
import java.awt.image.BufferedImage;
import java.io.IOException;
import java.io.InputStream;

@Mixin(TextureManager.class)
public class TextureManagerMixin {
    private static final Logger LOGGER = LogManager.getLogger("Skin64Beta");

    private static final String VANILLA_DEFAULT_SKIN = "/mob/char.png";
    private static final String TEST_SKIN_64X64 = "/assets/skin64beta/textures/LucyBeyondMe-64x64.png";
    private static final String TEST_SKIN_64X32 = "/assets/skin64beta/textures/LucyBeyondMe-64x32.png";

    @Inject(at = @At("HEAD"), method = "getTextureId", cancellable = true, remap = false)
    private void skin64beta$checkSkinHeight(String path, CallbackInfoReturnable<Integer> cir) {
        if (!path.equals(TEST_SKIN_64X64) && !path.equals(TEST_SKIN_64X32)) {
            return;
        }

        int height = readImageHeight(path);

        if (height != 64) {
            LOGGER.info("Rejected non-64x64 skin at {} (height was {}). Falling back to vanilla Steve.", path, height);
            TextureManager self = (TextureManager) (Object) this;
            int fallbackId = self.getTextureId(VANILLA_DEFAULT_SKIN);
            cir.setReturnValue(fallbackId);
        } else {
            LOGGER.info("Accepted 64x64 skin at {}.", path);
        }
    }

    private int readImageHeight(String path) {
        try (InputStream stream = TextureManagerMixin.class.getResourceAsStream(path)) {
            if (stream == null) {
                return -1;
            }
            BufferedImage image = ImageIO.read(stream);
            return image.getHeight();
        } catch (IOException e) {
            LOGGER.error("Failed to read image height for {}", path, e);
            return -1;
        }
    }
}